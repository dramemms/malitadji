import csv
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from ...models import Station, Commune





class Command(BaseCommand):
    help = "Importe les stations SHELL et COLIENERGY depuis un CSV (images Shell & Total)."

    def add_arguments(self, parser):
        parser.add_argument(
            "csv_path",
            type=str,
            help="Chemin du fichier CSV (stations_bamako_seed.csv)"
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simulation sans écriture en base"
        )

    @transaction.atomic
    def handle(self, *args, **options):
        csv_path = options["csv_path"]
        dry_run = options["dry_run"]

        try:
            f = open(csv_path, newline="", encoding="utf-8")
        except FileNotFoundError:
            raise CommandError(f"❌ Fichier introuvable : {csv_path}")

        created = 0
        updated = 0
        skipped = 0

        with f:
            reader = csv.DictReader(f)

            required_columns = {
                "station_name",
                "commune",
                "locality",
                "latitude",
                "longitude",
            }
            missing = required_columns - set(reader.fieldnames or [])
            if missing:
                raise CommandError(
                    f"❌ Colonnes manquantes dans le CSV : {sorted(missing)}"
                )

            for row in reader:
                name = (row.get("station_name") or "").strip()
                commune_label = (row.get("commune") or "").strip()
                address = (row.get("locality") or "").strip()

                if not name or not commune_label:
                    skipped += 1
                    continue

                # 🔹 Commune
                commune_obj, _ = Commune.objects.get_or_create(
                    nom=commune_label
                )

                # 🔹 Latitude / Longitude
                try:
                    latitude = float(row.get("latitude"))
                    longitude = float(row.get("longitude"))
                except (TypeError, ValueError):
                    skipped += 1
                    continue

                defaults = {
                    "commune": commune_obj,
                    "adresse": address,
                    "latitude": latitude,
                    "longitude": longitude,
                    # "gerant": None  # volontairement laissé vide
                }

                station, was_created = Station.objects.update_or_create(
                    nom=name,
                    commune=commune_obj,
                    defaults=defaults
                )

                if was_created:
                    created += 1
                else:
                    updated += 1

        if dry_run:
            transaction.set_rollback(True)
            self.stdout.write(
                self.style.WARNING("⚠️ DRY-RUN activé : aucune écriture en base")
            )

        self.stdout.write(self.style.SUCCESS(
            f"✅ Import terminé | Créées={created} | Mises à jour={updated} | Ignorées={skipped}"
        ))
