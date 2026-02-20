import json
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from shapely.geometry import shape, Point
from shapely.prepared import prep

from stations.models import Region, Cercle, Commune, Station


def _norm(s: str) -> str:
    return " ".join((s or "").strip().split())


def _get_lon_lat(feature: dict):
    """
    GeoJSON standard: feature["geometry"]["coordinates"] = [lon, lat]
    Ton fichier a aussi properties["@geometry"].
    """
    geom = feature.get("geometry")
    if geom and geom.get("type") == "Point":
        coords = geom.get("coordinates") or []
        if isinstance(coords, (list, tuple)) and len(coords) >= 2:
            return coords[0], coords[1]

    props = feature.get("properties") or {}
    g2 = props.get("@geometry")
    if isinstance(g2, dict) and g2.get("type") == "Point":
        coords = g2.get("coordinates") or []
        if isinstance(coords, (list, tuple)) and len(coords) >= 2:
            return coords[0], coords[1]

    return None, None


def _props_get(props: dict, *keys, default=None):
    for k in keys:
        v = props.get(k)
        if v is None:
            continue
        if isinstance(v, str):
            v = v.strip()
            if v:
                return v
        else:
            return v
    return default


class Command(BaseCommand):
    help = (
        "Remplace les stations par celles d'un GeoJSON, et affecte Commune/Cercle/Region "
        "via static/data/communes_mali.geojson (point-in-polygon)."
    )

    def add_arguments(self, parser):
        parser.add_argument("stations_geojson", type=str, help="Chemin du GeoJSON stations (614)")
        parser.add_argument(
            "--communes",
            type=str,
            default=str(Path("static") / "data" / "communes_mali.geojson"),
            help="Chemin du GeoJSON des communes Mali (polygones)",
        )
        parser.add_argument(
            "--purge-localisation",
            action="store_true",
            help="Supprime aussi Region/Cercle/Commune avant réimport (recommandé si tu as déjà importé 'Inconnue').",
        )

    @transaction.atomic
    def handle(self, *args, **opts):
        stations_path = Path(opts["stations_geojson"])
        communes_path = Path(opts["communes"])

        if not stations_path.exists():
            raise SystemExit(f"Fichier stations introuvable: {stations_path}")
        if not communes_path.exists():
            raise SystemExit(f"Fichier communes introuvable: {communes_path}")

        stations_data = json.loads(stations_path.read_text(encoding="utf-8"))
        communes_data = json.loads(communes_path.read_text(encoding="utf-8"))

        station_features = stations_data.get("features") or []
        commune_features = communes_data.get("features") or []

        self.stdout.write(self.style.SUCCESS(
            f"Stations: {len(station_features)} | Communes(polygones): {len(commune_features)}"
        ))

        # 1) Purge stations (cascade sur Stock, StockHistory, StationFollow, DeviceFollow)
        self.stdout.write("Suppression des stations existantes…")
        Station.objects.all().delete()

        if opts["purge_localisation"]:
            self.stdout.write(self.style.WARNING("Suppression Region/Cercle/Commune…"))
            Commune.objects.all().delete()
            Cercle.objects.all().delete()
            Region.objects.all().delete()

        # 2) Préparer les polygones communes (avec les BONNES clés)
        prepared_communes = []
        for cf in commune_features:
            cprops = cf.get("properties") or {}
            cgeom = cf.get("geometry")
            if not cgeom:
                continue

            poly = shape(cgeom)
            if poly.is_empty:
                continue

            # ✅ Mapping exact de tes données admin Mali
            commune_nom = _norm(_props_get(
                cprops,
                "adm3_name", "adm3_ref_name",
                default="Inconnue"
            ))
            cercle_nom = _norm(_props_get(
                cprops,
                "adm2_name",
                default="Inconnu"
            ))
            region_nom = _norm(_props_get(
                cprops,
                "adm1_name",
                default="Inconnue"
            ))

            prepared_communes.append({
                "commune_nom": commune_nom,
                "cercle_nom": cercle_nom,
                "region_nom": region_nom,
                "ppoly": prep(poly),  # prep pour accélérer covers()
            })

        # 3) Cache DB
        region_cache, cercle_cache, commune_cache = {}, {}, {}

        created = 0
        skipped = 0
        skipped_osm = 0
        skipped_noloc = 0
        skipped_outside = 0

        for sf in station_features:
            props = sf.get("properties") or {}

            # Nom (ton fichier stations a bien 'name')
            nom_station = _norm(_props_get(props, "name", "nom", default="Station"))

            # ❌ Exclure Station OSM (si jamais il y en a)
            low = nom_station.lower()
            if low in ["station osm", "osm station"] or low.startswith("station osm"):
                skipped += 1
                skipped_osm += 1
                continue

            # Coordonnées
            lon, lat = _get_lon_lat(sf)
            if lon is None or lat is None:
                skipped += 1
                skipped_noloc += 1
                continue

            pt = Point(float(lon), float(lat))

            # Trouver la commune qui couvre le point
            matched = None
            for item in prepared_communes:
                # ✅ covers() inclut les points sur la frontière
                if item["ppoly"].covers(pt):
                    matched = item
                    break

            if not matched:
                skipped += 1
                skipped_outside += 1
                continue

            region_nom = matched["region_nom"] or "Inconnue"
            cercle_nom = matched["cercle_nom"] or "Inconnu"
            commune_nom = matched["commune_nom"] or "Inconnue"

            # Adresse minimale (car ton GeoJSON stations n'a pas d'adresse)
            adresse = f"{commune_nom}, {cercle_nom}, {region_nom}"

            # Upsert Region/Cercle/Commune
            region = region_cache.get(region_nom)
            if not region:
                region, _ = Region.objects.get_or_create(nom=region_nom)
                region_cache[region_nom] = region

            cercle_key = (region.id, cercle_nom)
            cercle = cercle_cache.get(cercle_key)
            if not cercle:
                cercle, _ = Cercle.objects.get_or_create(region=region, nom=cercle_nom)
                cercle_cache[cercle_key] = cercle

            commune_key = (cercle.id, commune_nom)
            commune = commune_cache.get(commune_key)
            if not commune:
                commune, _ = Commune.objects.get_or_create(cercle=cercle, nom=commune_nom)
                commune_cache[commune_key] = commune

            Station.objects.create(
                nom=nom_station,
                commune=commune,
                adresse=adresse,
                latitude=float(lat),
                longitude=float(lon),
                gerant=None,
            )
            created += 1

        self.stdout.write(self.style.SUCCESS(
            f"Import terminé ✅ Créées: {created} | Ignorées: {skipped} "
            f"(OSM:{skipped_osm}, NoLoc:{skipped_noloc}, HorsMali:{skipped_outside})"
        ))
