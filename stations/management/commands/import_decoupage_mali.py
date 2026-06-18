import csv
import unicodedata
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from stations.models import Region, Cercle, Commune, Station


def clean(value):
    return str(value).strip() if value else ""


def normalize(value):
    value = clean(value).lower()
    value = unicodedata.normalize("NFKD", value)
    value = "".join(c for c in value if not unicodedata.combining(c))
    return " ".join(value.replace("-", " ").replace("'", " ").split())


class Command(BaseCommand):
    help = "Remplace le découpage administratif et rattache les stations"

    def add_arguments(self, parser):
        parser.add_argument("csv_file", type=str)

    @transaction.atomic
    def handle(self, *args, **options):
        csv_path = Path(options["csv_file"])

        if not csv_path.exists():
            self.stderr.write(self.style.ERROR(f"Fichier introuvable : {csv_path}"))
            return

        station_backup = []

        for station in Station.objects.select_related("commune"):
            station_backup.append({
                "id": station.id,
                "commune_name": station.commune.nom if station.commune else "",
            })

        Station.objects.update(commune=None)

        Commune.objects.all().delete()
        Cercle.objects.all().delete()
        Region.objects.all().delete()

        created_regions = 0
        created_cercles = 0
        created_communes = 0
        commune_index = {}

        with open(csv_path, newline="", encoding="latin1") as f:
            reader = csv.DictReader(f, delimiter=";")

            for row in reader:
                region_name = clean(row.get("REGIONS"))
                cercle_name = clean(row.get("CERCLES"))
                commune_name = clean(row.get("COMMUNES"))

                if not region_name or not cercle_name or not commune_name:
                    continue

                region, created = Region.objects.get_or_create(
                    nom=region_name
                )
                if created:
                    created_regions += 1

                cercle, created = Cercle.objects.get_or_create(
                    region=region,
                    nom=cercle_name
                )
                if created:
                    created_cercles += 1

                commune, created = Commune.objects.get_or_create(
                    cercle=cercle,
                    nom=commune_name
                )
                if created:
                    created_communes += 1

                commune_index[normalize(commune_name)] = commune

        attached = 0
        not_attached = []

        for item in station_backup:
            commune = commune_index.get(normalize(item["commune_name"]))

            if commune:
                Station.objects.filter(id=item["id"]).update(commune=commune)
                attached += 1
            else:
                not_attached.append(item)

        self.stdout.write(self.style.SUCCESS("Import terminé"))
        self.stdout.write(f"Régions créées : {created_regions}")
        self.stdout.write(f"Cercles créés : {created_cercles}")
        self.stdout.write(f"Communes créées : {created_communes}")
        self.stdout.write(f"Stations rattachées : {attached}")
        self.stdout.write(f"Stations non rattachées : {len(not_attached)}")

        if not_attached:
            self.stdout.write(self.style.WARNING("Stations non rattachées :"))
            for item in not_attached[:50]:
                self.stdout.write(
                    f"- Station ID {item['id']} | ancienne commune : {item['commune_name']}"
                )