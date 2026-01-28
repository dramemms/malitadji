# notifications/api_test.py
from __future__ import annotations

from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import csrf_exempt

from stations.models import DeviceFollow

from .utils import send_push_to_device_follows


@require_GET
def ping(request):
    return JsonResponse({"ok": True, "pong": True})


@csrf_exempt
@require_POST
def test_push(request):
    """
    Test: envoie un push à TOUS les devices qui ont un follow actif (toutes stations).
    """
    follows = DeviceFollow.objects.filter(is_active=True).select_related("device")

    res = send_push_to_device_follows(
        device_follows=follows,
        title="✅ Test push Malitadji",
        body="Si tu lis ça, Firebase FCM fonctionne ✅",
        data={"kind": "test_push"},
    )

    return JsonResponse(
        {
            "ok": True,
            "station_id": None,
            "produit": None,
            "target_devices": follows.values("device_id").distinct().count() if hasattr(follows, "values") else None,
            "result": res,
        }
    )
