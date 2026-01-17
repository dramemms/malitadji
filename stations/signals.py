from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.utils import timezone

from .models import (
    Stock,
    StockHistory,
    StationFollow,
    InAppNotification,
    DeviceToken,
)

from .push import send_push


# =====================================================
# 1) CAPTURE DE L'ANCIEN NIVEAU AVANT SAUVEGARDE
# =====================================================
@receiver(pre_save, sender=Stock)
def stock_capture_previous_level(sender, instance: Stock, **kwargs):
    if not instance.pk:
        instance._prev_niveau = None
        return

    old = Stock.objects.filter(pk=instance.pk).only("niveau").first()
    instance._prev_niveau = old.niveau if old else None


# =====================================================
# 2) HISTORIQUE + NOTIFICATION (PLEIN SEULEMENT)
# =====================================================
@receiver(post_save, sender=Stock)
def stock_history_and_notify(sender, instance: Stock, created: bool, **kwargs):
    prev_niveau = getattr(instance, "_prev_niveau", None)
    new_niveau = instance.niveau

    # -------------------------------------------------
    # (A) HISTORIQUE
    # -------------------------------------------------
    if created:
        StockHistory.objects.create(
            station=instance.station,
            produit=instance.produit,
            ancien_niveau=None,
            nouveau_niveau=new_niveau,
        )
    else:
        if prev_niveau == new_niveau:
            return

        StockHistory.objects.create(
            station=instance.station,
            produit=instance.produit,
            ancien_niveau=prev_niveau,
            nouveau_niveau=new_niveau,
        )

    # -------------------------------------------------
    # (B) CONDITION : NOTIFIER SEULEMENT SI "PLEIN"
    # -------------------------------------------------
    if new_niveau != "Plein":
        return

    if prev_niveau not in (None, "Rupture"):
        return

    # -------------------------------------------------
    # (C) UTILISATEURS QUI SUIVENT
    # -------------------------------------------------
    follows = (
        StationFollow.objects.filter(
            station=instance.station,
            is_active=True,
            produit=instance.produit,
        )
        |
        StationFollow.objects.filter(
            station=instance.station,
            is_active=True,
            produit__isnull=True,
        )
    )

    if not follows.exists():
        return

    # -------------------------------------------------
    # (D) CRÉATION DES NOTIFS + PUSH
    # -------------------------------------------------
    now_min = timezone.now().strftime("%Y%m%d%H%M")
    base_key = f"stock:{instance.station_id}:{instance.produit}:Plein:{now_min}"

    inapp_notifications = []

    for follow in follows.select_related("user"):
        title = "Stock plein ✅"
        message = (
            f"Bonne nouvelle ! La station {instance.station.nom} "
            f"a maintenant du {instance.produit.upper()} (PLEIN)."
        )

        event_key = f"{base_key}:user:{follow.user_id}"

        # ---- Notification In-App ----
        inapp_notifications.append(
            InAppNotification(
                user_id=follow.user_id,
                station=instance.station,
                produit=instance.produit,
                title=title,
                message=message,
                event_key=event_key,
            )
        )

        # ---- Notification PUSH ----
        tokens = list(
            DeviceToken.objects.filter(
                user_id=follow.user_id,
                is_active=True,
            ).values_list("token", flat=True)
        )

        if tokens:
            send_push(
                tokens,
                title,
                message,
                data={
                    "station_id": instance.station_id,
                    "produit": instance.produit,
                    "niveau": "Plein",
                },
            )

    # Bulk create (anti-doublon)
    if inapp_notifications:
        InAppNotification.objects.bulk_create(
            inapp_notifications,
            ignore_conflicts=True,
        )
