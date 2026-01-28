# notifications/utils.py
from __future__ import annotations

from typing import Iterable, Any

from django.utils import timezone

from firebase_admin import messaging

from stations.models import Device


def _safe_str(v: Any) -> str:
    # FCM data => dict[str,str] obligatoire
    return "" if v is None else str(v)


def _chunked(seq: list[str], size: int) -> list[list[str]]:
    return [seq[i : i + size] for i in range(0, len(seq), size)]


def _is_invalid_token_error(exc: Exception) -> bool:
    """
    Heuristique: firebase_admin lève souvent FirebaseError avec code,
    ou des messages contenant "registration token" / "not registered".
    On reste robuste sans dépendre de classes internes.
    """
    s = str(exc).lower()
    return any(
        k in s
        for k in (
            "registration token",
            "not registered",
            "invalid registration",
            "invalid argument",
            "unregistered",
            "mismatched-credential",
        )
    )


def _send_multicast(tokens: list[str], notification: messaging.Notification, data: dict[str, str]) -> dict:
    """
    Envoi multicast compatible:
    - essaie send_each_for_multicast (firebase_admin récent)
    - fallback: envoi 1 par 1
    Retourne: sent, fail, invalid, invalid_tokens
    """
    sent = 0
    fail = 0
    invalid = 0
    invalid_tokens: list[str] = []

    # ✅ méthode moderne
    try:
        msg = messaging.MulticastMessage(notification=notification, data=data, tokens=tokens)
        resp = messaging.send_each_for_multicast(msg)

        sent += int(getattr(resp, "success_count", 0) or 0)
        fail += int(getattr(resp, "failure_count", 0) or 0)

        # Identifier tokens invalides si possible
        responses = getattr(resp, "responses", None)
        if responses:
            for i, r in enumerate(responses):
                if getattr(r, "success", False):
                    continue
                exc = getattr(r, "exception", None)
                if exc and _is_invalid_token_error(exc):
                    invalid += 1
                    invalid_tokens.append(tokens[i])

        return {"sent": sent, "fail": fail, "invalid": invalid, "invalid_tokens": invalid_tokens}

    except AttributeError:
        # fallback plus bas
        pass

    # ✅ fallback: 1 par 1
    for t in tokens:
        msg = messaging.Message(notification=notification, data=data, token=t)
        try:
            messaging.send(msg)
            sent += 1
        except Exception as e:
            if _is_invalid_token_error(e):
                invalid += 1
                invalid_tokens.append(t)
            else:
                fail += 1

    return {"sent": sent, "fail": fail, "invalid": invalid, "invalid_tokens": invalid_tokens}


def send_push_to_device_follows(
    device_follows: Iterable,
    title: str,
    body: str,
    data: dict | None = None,
) -> dict:
    """
    device_follows: queryset/iterable de DeviceFollow (avec .device)
    On prend les device_id, puis on récupère tokens depuis stations.Device.fcm_token
    """
    device_ids: list[str] = []
    for df in device_follows:
        dev = getattr(df, "device", None)
        did = getattr(dev, "device_id", None)
        if did:
            device_ids.append(did)

    device_ids = sorted(set(device_ids))
    return send_fcm_to_device_ids(device_ids=device_ids, title=title, body=body, data=data or {})


def send_fcm_to_device_ids(
    device_ids: list[str],
    title: str,
    body: str,
    data: dict,
    *,
    cleanup_invalid_tokens: bool = True,
    batch_size: int = 450,  # marge (FCM limite 500)
) -> dict:
    """
    Envoie un push à une liste de device_ids (via stations.Device.fcm_token).

    - batch_size: FCM multicast <= 500 tokens; on garde une marge.
    - cleanup_invalid_tokens: si True, on vide Device.fcm_token pour les tokens invalides détectés.
    """
    now = timezone.now().isoformat()

    if not device_ids:
        return {"ok": True, "device_ids": [], "token_count": 0, "sent": 0, "fail": 0, "invalid": 0, "ts": now}

    qs = (
        Device.objects.filter(device_id__in=device_ids)
        .exclude(fcm_token__isnull=True)
        .exclude(fcm_token__exact="")
        .values_list("fcm_token", flat=True)
        .distinct()
    )
    tokens = list(qs)

    if not tokens:
        return {"ok": True, "device_ids": device_ids, "token_count": 0, "sent": 0, "fail": 0, "invalid": 0, "ts": now}

    safe_data = {str(k): _safe_str(v) for k, v in (data or {}).items()}
    notif = messaging.Notification(title=title, body=body)

    total_sent = 0
    total_fail = 0
    total_invalid = 0
    all_invalid_tokens: list[str] = []

    for chunk in _chunked(tokens, max(1, int(batch_size))):
        res = _send_multicast(chunk, notif, safe_data)
        total_sent += int(res["sent"])
        total_fail += int(res["fail"])
        total_invalid += int(res["invalid"])
        all_invalid_tokens.extend(res["invalid_tokens"])

    # Nettoyage optionnel: invalider ces tokens dans la table Device
    if cleanup_invalid_tokens and all_invalid_tokens:
        Device.objects.filter(fcm_token__in=all_invalid_tokens).update(fcm_token="")

    return {
        "ok": True,
        "device_ids": device_ids,
        "token_count": len(tokens),
        "sent": total_sent,
        "fail": total_fail,
        "invalid": total_invalid,
        "ts": now,
    }


# -------------------------------------------------------------------
# ✅ COMPATIBILITÉ: ancien nom utilisé par stations/signals.py
# -------------------------------------------------------------------
def send_fcm_to_devices(*, device_follows: Iterable, title: str, body: str, data: dict | None = None) -> dict:
    """
    Compat avec stations/signals.py (qui passe device_follows=...).
    """
    return send_push_to_device_follows(
        device_follows=device_follows,
        title=title,
        body=body,
        data=data or {},
    )


# (optionnel) helper si tu veux appeler avec device_ids ailleurs
def send_fcm_to_devices_by_ids(*, device_ids: list[str], title: str, body: str, data: dict | None = None) -> dict:
    return send_fcm_to_device_ids(
        device_ids=device_ids,
        title=title,
        body=body,
        data=data or {},
    )
