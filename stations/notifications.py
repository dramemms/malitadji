# stations/notifications.py
from __future__ import annotations

from django.db.models import Q

from .models import Stock, DeviceFollow
from notifications.utils import send_push_to_device_follows


def notify_station_available(stock: Stock, old_niveau: str | None = None) -> dict:
    """
    Règle (Option B / ton objectif final):
    - On notifie UNIQUEMENT quand le gérant met le niveau à "Plein"
    - et uniquement si l'ancien niveau n'était pas déjà "Plein"

    Ciblage:
    - DeviceFollow actifs de la station:
        * produit = stock.produit
        * OU produit IS NULL (abonnement "tous")
    """

    if not stock:
        return {"ok": False, "error": "stock missing"}

    # Sécurité: normaliser old_niveau
    old_niveau_norm = (old_niveau or "").strip()

    # ✅ règle: uniquement quand ça devient Plein
    if stock.niveau != "Plein":
        return {"ok": True, "skipped": True, "reason": "niveau_not_plein"}

    # ✅ pas de push si c'était déjà Plein
    if old_niveau_norm == "Plein":
        return {"ok": True, "skipped": True, "reason": "already_plein"}

    station_id = stock.station_id
    produit = (stock.produit or "").strip().lower()  # "essence" / "gasoil"

    # si produit vide (ne devrait pas arriver avec tes choices), on traite comme "tous"
    produit_filter = Q(produit__isnull=True) if not produit else (Q(produit__isnull=True) | Q(produit=produit))

    follows_qs = (
        DeviceFollow.objects.filter(
            station_id=station_id,
            is_active=True,
        )
        .filter(produit_filter)
        .select_related("device")
    )

    # Message
    station_name = getattr(stock.station, "nom", None) or f"Station #{station_id}"
    if produit:
        body = f"{station_name} : {produit} est maintenant disponible (Plein)."
    else:
        body = f"{station_name} : carburant disponible (Plein)."

    title = "✅ Carburant disponible"

    # Envoi push (ta fonction doit récupérer les tokens via device.fcm_token ou DeviceToken)
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
