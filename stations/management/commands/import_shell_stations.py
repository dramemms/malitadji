import csv
from pathlib import Path
from django.core.management.base import BaseCommand
from django.db import transaction

from stations.models import Region, Cercle, Commune, Station


class Command(BaseCommand):
    help = "Import des stations Shell avec Region / Cercle / Commune"

    def add_arguments(self, parser):
        parser.add_argument("csv_path", type=str)
        parser.add_argument(
            "--update",
            action="store_true",
            help="Mettre à jour latitude/longitude si la station existe"
        )

    @transaction.atomic
    def handle(self, *args, **options):
        path = Path(options["csv_path"])
        update = options["update"]

        created = updated = skipped = 0

        if not path.exists():
            self.stderr.write(self.style.ERROR(f"Fichier introuvable : {path}"))
            return

        with open(path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)

            required_cols = {
                "nom_station", "region", "cercle",
                "commune", "latitude", "longitude"
            }
            if not required_cols.issubset(reader.fieldnames):
                self.stderr.write(
                    self.style.ERROR(
                        f"Colonnes requises : {', '.join(required_cols)}"
                    )
                )
                return

            for row in reader:
                nom = row["nom_station"].strip()
                region_name = row["region"].strip()
                cercle_name = row["cercle"].strip()
                commune_name = row["commune"].strip()
                adresse = row.get("adresse", "").strip()

                # --- coordonnées
                try:
                    latitude = float(row["latitude"])
                    longitude = float(row["longitude"])
                except ValueError:
                    skipped += 1
                    continue

                # --- Région
                region = Region.objects.filter(
                    nom__iexact=region_name
                ).first()
                if not region:
                    self.stderr.write(f"❌ Région introuvable : {region_name}")
                    skipped += 1
                    continue

                # --- Cercle
                cercle = Cercle.objects.filter(
                    nom__iexact=cercle_name,
                    region=region
                ).first()
                if not cercle:
                    self.stderr.write(
                        f"❌ Cercle introuvable : {cercle_name} ({region_name})"
                    )
                    skipped += 1
                    continue

                # --- Commune
                commune = Commune.objects.filter(
                    nom__iexact=commune_name,
                    cercle=cercle
                ).first()
                if not commune:
                    self.stderr.write(
                        f"❌ Commune introuvable : {commune_name} ({cercle_name})"
                    )
                    skipped += 1
                    continue

                # --- Station
                qs = Station.objects.filter(
                    nom__iexact=nom,
                    commune=commune
                )

                if qs.exists():
                    if update:
                        station = qs.first()
                        station.latitude = latitude
                        station.longitude = longitude
                        station.adresse = adresse
                        station.save()
                        updated += 1
                    else:
                        skipped += 1
                else:
                    Station.objects.create(
                        nom=nom,
                        commune=commune,
                        adresse=adresse,
                        latitude=latitude,
                        longitude=longitude,
                    )
                    created += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"✅ Import terminé | Créées={created} | "
                f"Mises à jour={updated} | Ignorées={skipped}"
            )
        )
