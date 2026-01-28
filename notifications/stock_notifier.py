# notifications/stock_notifier.py
from django.db.models import Q
from stations.models import DeviceFollow, Device
from notifications.fcm import envoyer_notif_stock

def notifier_devices_station(station_id: int, produit: str | None, title: str, body: str):
    """
    Notifie tous les appareils qui suivent cette station.
    - Si produit est fourni (essence/gasoil), on notifie:
      * ceux qui suivent "tous" (produit NULL)
      * et ceux qui suivent spécifiquement ce produit
    """
    follows = DeviceFollow.objects.filter(station_id=station_id, is_active=True)

    if produit:
        follows = follows.filter(Q(produit__isnull=True) | Q(produit=produit))

    device_ids = follows.values_list("device_id", flat=True)

    tokens = list(
        Device.objects.filter(id__in=device_ids, is_active=True)
        .exclude(fcm_token__isnull=True)
        .exclude(fcm_token__exact="")
        .values_list("fcm_token", flat=True)
    )

    return envoyer_notif_stock(
        tokens=tokens,
        title=title,
        body=body,
        data={"station_id": str(station_id), "produit": produit or ""}
    )
