import json
from pathlib import Path

from django.core.management.base import BaseCommand
from django.conf import settings

from shapely.geometry import Point, shape

from stations.models import Region, Cercle, Commune, Station


class Command(BaseCommand):
    help = (
        "Importe les stations-service OSM du Mali et les associe "
        "automatiquement aux Régions, Cercles et Communes (données HDX)."
    )

    def load_geojson(self, filename):
        """Charge un fichier GeoJSON depuis static/data/"""
        path = Path(settings.BASE_DIR) / "static" / "data" / filename
        if not path.exists():
            self.stderr.write(self.style.ERROR(f"Fichier introuvable : {path}"))
            return None

        self.stdout.write(self.style.SUCCESS(f"Chargement de {filename}..."))
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def find_unit(self, point, geojson):
        """Trouve l’unité administrative contenant un point"""
        for feat in geojson["features"]:
            polygon = shape(feat["geometry"])
            if polygon.contains(point):
                return feat["properties"]
        return None

    def handle(self, *args, **options):
        # 1️⃣ Chargement des fichiers HDX
        regions_geo = self.load_geojson("regions_mali.geojson")
        cercles_geo = self.load_geojson("cercles_mali.geojson")
        communes_geo = self.load_geojson("communes_mali.geojson")

        if not regions_geo or not cercles_geo or not communes_geo:
            self.stderr.write(
                self.style.ERROR(
                    "Impossible de charger les fichiers administratifs HDX."
                )
            )
            return

        # 2️⃣ Chargement du fichier des stations OSM
        stations_path = (
            Path(settings.BASE_DIR) / "static" / "data" / "stations_mali.geojson"
        )

        if not stations_path.exists():
            self.stderr.write(self.style.ERROR("stations_mali.geojson introuvable"))
            return

        self.stdout.write(self.style.SUCCESS("Chargement des stations OSM..."))
        with open(stations_path, "r", encoding="utf-8") as f:
            stations_data = json.load(f)
        features = stations_data.get("features", [])

        created = 0

        # --- petite fonction utilitaire pour choisir le bon champ de nom ---
        def pick_name(props, candidates, level):
            for key in candidates:
                if key in props and props[key]:
                    return props[key]
            print(
                f"[WARN] Impossible de trouver un nom pour {level} avec propriétés :",
                props,
            )
            return None

        # 3️⃣ Parcours des stations
        for feat in features:
            geom = feat.get("geometry")
            props = feat.get("properties", {})

            if not geom or geom.get("type") != "Point":
                continue

            lon, lat = geom["coordinates"]
            point = Point(lon, lat)

            # 4️⃣ Trouver les limites administratives HDX
            commune_props = self.find_unit(point, communes_geo)
            cercle_props = self.find_unit(point, cercles_geo)
            region_props = self.find_unit(point, regions_geo)

            if not commune_props or not cercle_props or not region_props:
                continue

            # 🧠 Clés possibles d’après tes fichiers HDX
            #   (pour les régions on a vu: adm1_name, adm1_name1, adm1_name2, adm1_name3, ...)
            region_name = pick_name(
                region_props,
                ["adm1_name", "adm1_name1", "adm1_name2", "adm1_name3", "adm1_ref_name"],
                "région",
            )
            cercle_name = pick_name(
                cercle_props,
                [
                    "adm2_name",
                    "adm2_name1",
                    "adm2_name2",
                    "adm2_name3",
                    "adm2_ref_name",
                ],
                "cercle",
            )
            commune_name = pick_name(
                commune_props,
                [
                    "adm3_name",
                    "adm3_name1",
                    "adm3_name2",
                    "adm3_name3",
                    "adm3_ref_name",
                ],
                "commune",
            )

            if not (region_name and cercle_name and commune_name):
                # on ne peut pas rattacher proprement cette station
                continue

            # 5️⃣ Création Région → Cercle → Commune
            region_obj, _ = Region.objects.get_or_create(nom=region_name)
            cercle_obj, _ = Cercle.objects.get_or_create(
                nom=cercle_name, region=region_obj
            )
            commune_obj, _ = Commune.objects.get_or_create(
                nom=commune_name, cercle=cercle_obj
            )

            # 6️⃣ Création de la station
            nom_station = props.get("name") or "Station OSM"

            station, created_flag = Station.objects.get_or_create(
                nom=nom_station,
                commune=commune_obj,
                defaults={
                    "latitude": lat,
                    "longitude": lon,
                },
            )

            if created_flag:
                created += 1

        self.stdout.write(
            self.style.SUCCESS(f"Import terminé : {created} stations OSM créées.")
        )
