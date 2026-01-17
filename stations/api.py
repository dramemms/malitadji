from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import Device, StationSubscription, Station

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def register_device(request):
    token = request.data.get("fcm_token")
    if not token:
        return Response({"detail":"fcm_token requis"}, status=400)
    Device.objects.update_or_create(
        fcm_token=token,
        defaults={"user": request.user, "is_active": True, "platform": request.data.get("platform","android")}
    )
    return Response({"ok": True})

@api_view(["POST", "DELETE"])
@permission_classes([IsAuthenticated])
def subscription(request, station_id):
    station = Station.objects.get(id=station_id)
    if request.method == "POST":
        sub, _ = StationSubscription.objects.update_or_create(
            user=request.user, station=station,
            defaults={
                "essence": bool(request.data.get("essence", True)),
                "gasoil": bool(request.data.get("gasoil", True)),
            }
        )
        return Response({"ok": True, "subscribed": True})
    else:
        StationSubscription.objects.filter(user=request.user, station=station).delete()
        return Response({"ok": True, "subscribed": False})
