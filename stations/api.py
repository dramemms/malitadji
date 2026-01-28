# stations/api.py
from __future__ import annotations

from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import Device, DeviceFollow, Station


def _norm_produit(p) -> str | None:
    if p is None:
        return None
    s = str(p).strip().lower()
    if not s:
        return None
    if "gaso" in s or "diesel" in s:
        return "gasoil"
    if "ess" in s or "super":
        # attention: "or 'super'" serait toujours True, donc on fait bien un test:
        pass
    if "ess" in s or "super" in s:
        return "essence"
    return s


def _validate_produit(p: str | None) -> str | None:
    """
    Autorise: None / essence / gasoil
    """
    if p is None:
        return None
    p = _norm_produit(p)
    if p in (None, "essence", "gasoil"):
        return p
    return "__invalid__"


def _get_device_id(request) -> str | None:
    return request.headers.get("X-DEVICE-ID") or request.META.get("HTTP_X_DEVICE_ID")


@api_view(["POST"])
@permission_classes([AllowAny])
def register_device(request):
    """
    POST /api/device/register/
    Body: device_id, platform, fcm_token
    """
    device_id = request.data.get("device_id")
    platform = request.data.get("platform", "android")
    token = request.data.get("fcm_token")

    if not device_id:
        return Response({"ok": False, "detail": "device_id requis"}, status=400)
    if not token:
        return Response({"ok": False, "detail": "fcm_token requis"}, status=400)

    dev, _ = Device.objects.update_or_create(
        device_id=device_id,
        defaults={
            "platform": platform,
            "fcm_token": token,
            "is_active": True,
            "last_seen_at": timezone.now(),
        },
    )

    return Response({"ok": True, "device_id": dev.device_id})


@api_view(["POST"])
@permission_classes([AllowAny])
def follow_station(request, station_id: int):
    """
    POST /api/device/follow/<station_id>/
    Header: X-DEVICE-ID: <uuid>
    Body: {} OR {"produit":"essence"} OR {"produit":"gasoil"} OR {"produit":null}
    """
    device_id = _get_device_id(request)
    if not device_id:
        return Response({"ok": False, "detail": "Header X-DEVICE-ID requis"}, status=400)

    station = Station.objects.filter(id=station_id).first()
    if not station:
        return Response({"ok": False, "detail": "Station introuvable"}, status=404)

    produit = request.data.get("produit", None)
    produit_norm = _validate_produit(produit)
    if produit_norm == "__invalid__":
        return Response({"ok": False, "detail": "produit invalide (essence|gasoil|null)"}, status=400)

    dev = Device.objects.filter(device_id=device_id).first()
    if not dev:
        return Response({"ok": False, "detail": "Device non enregistré. Appelle /api/device/register/ d'abord."}, status=400)

    # ping last_seen
    Device.objects.filter(id=dev.id).update(last_seen_at=timezone.now(), is_active=True)

    obj, _ = DeviceFollow.objects.update_or_create(
        device=dev,
        station=station,
        produit=produit_norm,  # None => tous
        defaults={"is_active": True},
    )

    return Response({
        "ok": True,
        "followed": True,
        "station_id": station.id,
        "produit": obj.produit,
    })


@api_view(["POST"])
@permission_classes([AllowAny])
def unfollow_station(request, station_id: int):
    """
    POST /api/device/unfollow/<station_id>/
    Header: X-DEVICE-ID
    Body: {} OR {"produit":"essence"} OR {"produit":"gasoil"} OR {"produit":null}
    """
    device_id = _get_device_id(request)
    if not device_id:
        return Response({"ok": False, "detail": "Header X-DEVICE-ID requis"}, status=400)

    station = Station.objects.filter(id=station_id).first()
    if not station:
        return Response({"ok": False, "detail": "Station introuvable"}, status=404)

    produit = request.data.get("produit", None)
    produit_norm = _validate_produit(produit)
    if produit_norm == "__invalid__":
        return Response({"ok": False, "detail": "produit invalide (essence|gasoil|null)"}, status=400)

    dev = Device.objects.filter(device_id=device_id).first()
    if not dev:
        return Response({"ok": False, "detail": "Device non enregistré"}, status=400)

    Device.objects.filter(id=dev.id).update(last_seen_at=timezone.now())

    updated = DeviceFollow.objects.filter(
        device=dev, station=station, produit=produit_norm
    ).update(is_active=False)

    return Response({"ok": True, "unfollowed": True, "count": updated})


@api_view(["GET"])
@permission_classes([AllowAny])
def my_follows(request):
    """
    GET /api/device/follows/
    Header: X-DEVICE-ID
    -> liste les abonnements actifs du device
    """
    device_id = _get_device_id(request)
    if not device_id:
        return Response({"ok": False, "detail": "Header X-DEVICE-ID requis"}, status=400)

    dev = Device.objects.filter(device_id=device_id).first()
    if not dev:
        return Response({"ok": False, "detail": "Device non enregistré"}, status=400)

    Device.objects.filter(id=dev.id).update(last_seen_at=timezone.now())

    qs = (
        DeviceFollow.objects
        .filter(device=dev, is_active=True)
        .select_related("station", "station__commune")
        .order_by("station__nom")
    )

    items = []
    for df in qs:
        items.append({
            "id": df.id,
            "station_id": df.station_id,
            "station_nom": df.station.nom,
            "commune": str(df.station.commune),
            "produit": df.produit,  # None => tous
        })

    return Response({"ok": True, "device_id": dev.device_id, "count": len(items), "items": items})
