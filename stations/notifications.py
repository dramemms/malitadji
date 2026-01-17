from .models import StationSubscription, Device

def notify_station_available(stock):
    station = stock.station
    produit = stock.produit

    subs = StationSubscription.objects.filter(
        station=station,
        **{produit: True}
    ).select_related("user")

    for sub in subs:
        devices = Device.objects.filter(user=sub.user, is_active=True)

        for device in devices:
            # Pour l'instant : log (test)
            print(
                f"🔔 NOTIF → {sub.user.username} | "
                f"{station.nom} | {produit.upper()} DISPONIBLE"
            )

            # 🔜 plus tard :
            # send_push_fcm(device.fcm_token, ...)
