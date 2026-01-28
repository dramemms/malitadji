# stations/api_device.py
import json
from typing import Any

from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction

from .models import Device, DeviceFollow

DEBUG_DEVICE_API = False


def _dbg(*args):
    if DEBUG_DEVICE_API:
        print(*args)


def _read_json(request) -> dict[str, Any]:
    """
    Lit le JSON du body (curl / Flutter / web).
    Si body vide ou invalide -> {}.
    """
    try:
        raw = request.body or b""
        if not raw:
            return {}
        return json.loads(raw.decode("utf-8"))
    except Exception as e:
        _dbg("DEBUG _read_json error:", e)
        return {}


def _normalize_produit(p: Any) -> str | None:
    """
    Normalise 'produit' -> 'essence' / 'gasoil' / None
    Tolère guillemets + espaces.
    """
    if p is None:
        return None

    s = str(p).strip()
    s = s.strip('"').strip("'").strip()
    s = s.lower().strip()
    if not s:
        return None

    if s in ("diesel", "gazole", "gazoil"):
        s = "gasoil"

    if s not in ("essence", "gasoil"):
        return None
    return s


def _get_device_id(request) -> str | None:
    return request.headers.get("X-DEVICE-ID") or request.META.get("HTTP_X_DEVICE_ID")


@csrf_exempt
@require_POST
def device_register(request):
    """
    Enregistre/maj un device + token FCM.
    Accepte JSON ou form-data.
    Headers: X-DEVICE-ID (optionnel si device_id envoyé dans body)
    JSON: {"device_id": "...", "platform":"android", "fcm_token":"..."}
    """
    payload = _read_json(request) or request.POST.dict()

    device_id = _get_device_id(request) or payload.get("device_id") or request.POST.get("device_id")
    if not device_id:
        return JsonResponse({"ok": False, "error": "device_id missing"}, status=400)

    platform = (payload.get("platform") or request.POST.get("platform") or "android").strip()
    fcm_token = (payload.get("fcm_token") or request.POST.get("fcm_token") or "").strip()

    device, created = Device.objects.get_or_create(device_id=device_id)

    changed = False
    if platform and device.platform != platform:
        device.platform = platform
        changed = True

    # si token vide -> ne remplace pas
    if fcm_token and device.fcm_token != fcm_token:
        device.fcm_token = fcm_token
        changed = True

    if changed:
        device.save()

    return JsonResponse(
        {
            "ok": True,
            "device_id": device.device_id,
            "created": created,
            "platform": device.platform,
            "has_fcm_token": bool(device.fcm_token),
        }
    )


@csrf_exempt
@require_GET
def list_follows(request):
    """
    Liste les abonnements d'un device.
    """
    device_id = _get_device_id(request)
    if not device_id:
        return JsonResponse({"ok": False, "error": "X-DEVICE-ID missing"}, status=400)

    qs = (
        DeviceFollow.objects.filter(device__device_id=device_id, is_active=True)
        .values("station_id", "produit", "is_active")
        .order_by("station_id", "produit")
    )
    return JsonResponse({"ok": True, "device_id": device_id, "count": qs.count(), "items": list(qs)})


@csrf_exempt
@require_POST
def device_follow(request, station_id: int):
    """
    Abonne un device à une station.
    Règle:
    - si produit est précisé, on désactive le follow global (produit NULL) actif.
    """
    device_id = _get_device_id(request)
    if not device_id:
        return JsonResponse({"ok": False, "error": "X-DEVICE-ID missing"}, status=400)

    payload = _read_json(request) or request.POST.dict()
    produit_raw = payload.get("produit")
    produit = _normalize_produit(produit_raw)

    _dbg("DEBUG body =", request.body)
    _dbg("DEBUG payload =", payload)
    _dbg("DEBUG produit_raw =", produit_raw, "=> produit_norm =", produit)

    device, _ = Device.objects.get_or_create(device_id=device_id)

    with transaction.atomic():
        # Si on suit un produit précis => on coupe le global (NULL)
        if produit:
            DeviceFollow.objects.filter(
                device=device,
                station_id=station_id,
                produit__isnull=True,
                is_active=True,
            ).update(is_active=False)

        follow, created = DeviceFollow.objects.update_or_create(
            device=device,
            station_id=station_id,
            produit=produit,
            defaults={"is_active": True},
        )

    return JsonResponse(
        {
            "ok": True,
            "followed": True,
            "station_id": station_id,
            "produit": follow.produit,  # "essence"/"gasoil"/None
            "is_active": follow.is_active,
            "created": created,
            "device_id": device_id,
        }
    )


@csrf_exempt
@require_POST
def unfollow_station(request, station_id: int):
    """
    Désactive tous les follows (global + produits) pour une station sur un device.
    """
    device_id = _get_device_id(request)
    if not device_id:
        return JsonResponse({"ok": False, "error": "X-DEVICE-ID missing"}, status=400)

    updated = DeviceFollow.objects.filter(
        device__device_id=device_id,
        station_id=station_id,
        is_active=True,
    ).update(is_active=False)

    return JsonResponse({"ok": True, "unfollowed": True, "station_id": station_id, "updated": updated})
