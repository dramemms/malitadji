# stations/api_geojson.py
from __future__ import annotations

from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.db.models import Exists, OuterRef, Max, Q

from .models import Station, Stock, StationFollow


def _map_niveau_to_statut(niveau: str | None) -> str:
    """
    Tes niveaux: Bas, Faible, Plein, Rupture
    -> on renvoie: dispo, faible, rupture, inconnu
    """
    if not niveau:
        return "inconnu"

    n = str(niveau).strip().lower()

    if n == "rupture":
        return "rupture"
    if n in ("faible", "bas"):
        return "faible"
    if n == "plein":
        return "dispo"
    return "inconnu"


def _status_global(essence_statut: str, gasoil_statut: str) -> str:
    """
    Pour la couleur globale (optionnel dans properties["status"]):
    - si rupture (un des deux) => Rupture
    - sinon si faible (un des deux) => Faible
    - sinon si dispo (un des deux) => Disponible
    - sinon => Inconnu
    """
    e = (essence_statut or "inconnu").lower()
    g = (gasoil_statut or "inconnu").lower()

    if e == "rupture" or g == "rupture":
        return "Rupture"
    if e == "faible" or g == "faible":
        return "Faible"
    if e == "dispo" or g == "dispo":
        return "Disponible"
    return "Inconnu"


@require_GET
def stations_geojson(request):
    # --- filtres IDs (ceux de ta carte.html) ---
    region_id = request.GET.get("region")
    cercle_id = request.GET.get("cercle")
    commune_id = request.GET.get("commune")
    statut = request.GET.get("statut")  # dispo/faible/rupture (optionnel)

    qs = (
        Station.objects
        .select_related("commune__cercle__region")
        .exclude(Q(latitude__isnull=True) | Q(longitude__isnull=True))
        .annotate(derniere_maj=Max("stocks__date_maj"))
    )

    if region_id:
        qs = qs.filter(commune__cercle__region_id=region_id)
    if cercle_id:
        qs = qs.filter(commune__cercle_id=cercle_id)
    if commune_id:
        qs = qs.filter(commune_id=commune_id)

    # is_followed: true si l'utilisateur suit la station (peu importe produit)
    if request.user.is_authenticated:
        qs = qs.annotate(
            is_followed=Exists(
                StationFollow.objects.filter(
                    user=request.user,
                    station_id=OuterRef("pk"),
                    is_active=True,
                )
            )
        )
    else:
        qs = qs.annotate(is_followed=Exists(StationFollow.objects.none()))

    # On récupère les stocks actuels (1 par produit)
    station_ids = list(qs.values_list("id", flat=True))

    stock_by_station: dict[int, dict[str, dict[str, object]]] = {}

    if station_ids:
        stocks = (
            Stock.objects
            .filter(station_id__in=station_ids)
            .values("station_id", "produit", "niveau", "date_maj")
        )

        for row in stocks:
            sid = row["station_id"]
            prod = row["produit"]  # attendu: "essence" ou "gasoil"
            niveau = row["niveau"]
            date_maj = row["date_maj"]

            if sid not in stock_by_station:
                stock_by_station[sid] = {
                    "essence": {"statut": "inconnu", "date_maj": None},
                    "gasoil": {"statut": "inconnu", "date_maj": None},
                }

            # on ne remplit que si prod est bien "essence" ou "gasoil"
            if prod in ("essence", "gasoil"):
                stock_by_station[sid][prod] = {
                    "statut": _map_niveau_to_statut(niveau),
                    "date_maj": date_maj,
                }

    features = []

    wanted = (statut or "").strip().lower()  # dispo/faible/rupture/""

    for s in qs:
        st = stock_by_station.get(
            s.id,
            {
                "essence": {"statut": "inconnu", "date_maj": None},
                "gasoil": {"statut": "inconnu", "date_maj": None},
            },
        )

        essence_statut = (st.get("essence") or {}).get("statut", "inconnu")
        gasoil_statut = (st.get("gasoil") or {}).get("statut", "inconnu")

        # filtre statut optionnel (statut = dispo/faible/rupture)
        if wanted:
            if wanted == "dispo" and not (essence_statut == "dispo" or gasoil_statut == "dispo"):
                continue
            if wanted == "faible" and not (essence_statut == "faible" or gasoil_statut == "faible"):
                continue
            if wanted == "rupture" and not (essence_statut == "rupture" or gasoil_statut == "rupture"):
                continue

        status_pin = _status_global(essence_statut, gasoil_statut)

        # sécurité conversion float
        try:
            lng = float(s.longitude)
            lat = float(s.latitude)
        except (TypeError, ValueError):
            continue

        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [lng, lat],
            },
            "properties": {
                "id": s.id,
                "nom": s.nom,
                "adresse": s.adresse,

                # Noms
                "region": s.commune.cercle.region.nom if s.commune and s.commune.cercle and s.commune.cercle.region else None,
                "cercle": s.commune.cercle.nom if s.commune and s.commune.cercle else None,
                "commune": s.commune.nom if s.commune else None,

                # IDs (pour filtrage fiable)
                "region_id": s.commune.cercle.region_id if s.commune and s.commune.cercle else None,
                "cercle_id": s.commune.cercle_id if s.commune else None,
                "commune_id": s.commune_id,

                # Stocks normalisés pour ton JS (dispo/faible/rupture/inconnu)
                "essence": essence_statut,
                "gasoil": gasoil_statut,

                # Dernière MAJ globale
                "derniere_maj": s.derniere_maj.isoformat() if getattr(s, "derniere_maj", None) else None,

                # Statut global lisible (optionnel)
                "status": status_pin,

                # Suivi (popup)
                "is_followed": bool(getattr(s, "is_followed", False)),
            },
        })

    return JsonResponse({"type": "FeatureCollection", "features": features})
