# stations/notifications.py
from __future__ import annotations

from django.db.models import Q

from .models import Stock, DeviceFollow
from notifications.utils import send_push_to_device_follows


def _station_notification_location(stock: Stock) -> str:
    station = stock.station

    station_name = getattr(station, "nom", None) or f"Station #{stock.station_id}"

    commune = getattr(station, "commune", None)

    if not commune:
        return station_name

    commune_name = commune.nom

    region_name = ""
    if commune.cercle and commune.cercle.region:
        region_name = commune.cercle.region.nom

    if region_name:
        return f"{station_name}, {commune_name} ({region_name})"

    return f"{station_name}, {commune_name}"


def notify_station_available(stock: Stock, old_niveau: str | None = None) -> dict:
    if not stock:
        return {"ok": False, "error": "stock missing"}

    old_niveau_norm = (old_niveau or "").strip()

    if stock.niveau != "Plein":
        return {"ok": True, "skipped": True, "reason": "niveau_not_plein"}

    if old_niveau_norm == "Plein":
        return {"ok": True, "skipped": True, "reason": "already_plein"}

    station_id = stock.station_id
    produit = (stock.produit or "").strip().lower()

    produit_filter = (
        Q(produit__isnull=True)
        if not produit
        else Q(produit__isnull=True) | Q(produit=produit)
    )

    follows_qs = (
        DeviceFollow.objects.filter(
            station_id=station_id,
            is_active=True,
        )
        .filter(produit_filter)
        .select_related(
            "device",
            "station__commune__cercle__region",
        )
    )

    location = _station_notification_location(stock)
    produit_label = produit.capitalize() if produit else "Carburant"

    body = f"{location} : {produit_label} → Plein"
    title = "Carburant disponible"

    return send_push_to_device_follows(
        device_follows=follows_qs,
        title=title,
        body=body,
        data={
            "kind": "stock_available",
            "station_id": str(station_id),
            "produit": produit or "",
            "niveau": "Plein",
        },
    )