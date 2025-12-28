import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from stations.models import Region, Cercle, Commune, Station


class Command(BaseCommand):
    help = "Importe des stations depuis un fichier GeoJSON (Point) vers le modèle Station."

    def add_arguments(self, parser):
        parser.add_argument("geojson_path", type=str, help="Chemin du fichier .geojson")
        parser.add_argument(
            "--commune-id",
            type=int,
            default=None,
            help="ID d'une commune existante à utiliser pour toutes les stations importées",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        geojson_path = Path(options["geojson_path"])
        if not geojson_path.exists():
            raise CommandError(f"Fichier introuvable: {geojson_path}")

        # Lire GeoJSON (UTF-8) — si souci d'encodage, essayer utf-8-sig
        try:
            raw = geojson_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            raw = geojson_path.read_text(encoding="utf-8-sig")

        data = json.loads(raw)
        features = data.get("features", [])
        if not features:
            raise CommandError("Aucune feature trouvée dans le GeoJSON.")

        # Commune cible (obligatoire car Station.commune n'est pas null)
        commune_id = options["commune_id"]
        if commune_id:
            commune = Commune.objects.get(pk=commune_id)
        else:
            # Crée/Utilise une commune "Non renseignée"
            region, _ = Region.objects.get_or_create(nom="Non renseignée")
            cercle, _ = Cercle.objects.get_or_create(nom="Non renseigné", region=region)
            commune, _ = Commune.objects.get_or_create(nom="Non renseignée", cercle=cercle)

        created = 0
        updated = 0
        skipped = 0

        for f in features:
            geom = f.get("geometry") or {}
            if geom.get("type") != "Point":
                skipped += 1
                continue

            coords = geom.get("coordinates") or []
            if len(coords) != 2:
                skipped += 1
                continue

            lng, lat = coords[0], coords[1]
            props = f.get("properties") or {}

            name = (props.get("name") or props.get("name:fr") or "").strip()
            if not name:
                # Si pas de nom, on met un nom par défaut avec l'id OSM si dispo
                name = (props.get("@id") or f.get("id") or "Station").strip()

            adresse = (props.get("addr:full") or props.get("addr:street") or "").strip()

            # Anti-doublon : (nom + lat + lng)
            obj, was_created = Station.objects.update_or_create(
                nom=name,
                latitude=float(lat),
                longitude=float(lng),
                defaults={
                    "commune": commune,
                    "adresse": adresse or None,
                },
            )

            if was_created:
                created += 1
            else:
                updated += 1

        self.stdout.write(self.style.SUCCESS(
            f"Import terminé ✅  créées={created}  mises_à_jour={updated}  ignorées={skipped}  commune='{commune}'"
        ))
