import json
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt

from .models import DeviceToken


@csrf_exempt
@require_POST
def register_fcm_token(request):
    """
    Enregistre / met à jour un token FCM Android.
    (Sans auth pour l'instant – OK en dev)
    """
    try:
        data = json.loads(request.body.decode("utf-8"))

        token = (data.get("token") or "").strip()
        platform = (data.get("platform") or "android").strip().lower()

        if not token:
            return JsonResponse({"ok": False, "error": "missing token"}, status=400)

        obj, created = DeviceToken.objects.update_or_create(
            token=token,
            defaults={"platform": platform},
        )

        return JsonResponse({
            "ok": True,
            "created": created,
        })
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=400)
