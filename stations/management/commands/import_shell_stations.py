import pandas as pd
from django.core.management.base import BaseCommand
from stations.models import Region, Cercle, Commune, Station, Stock


class Command(BaseCommand):
    help = "Supprime les anciennes stations Shell et importe le référentiel Shell depuis Excel"

    def add_arguments(self, parser):
        parser.add_argument("excel_file", type=str)

    def handle(self, *args, **options):
        excel_file = options["excel_file"]

        self.stdout.write("Suppression des anciennes stations Shell...")
        deleted, _ = Station.objects.filter(nom__icontains="shell").delete()
        self.stdout.write(self.style.WARNING(f"{deleted} anciennes données supprimées."))

        df = pd.read_excel(excel_file)

        created = 0
        errors = 0

        for index, row in df.iterrows():
            try:
                region_nom = str(row["Région"]).strip()
                cercle_nom = str(row["Cercle"]).strip()
                commune_nom = str(row["Commune"]).strip()
                station_nom = str(row["Nom de la station"]).strip()
                latitude = float(row["Latitude"])
                longitude = float(row["Longitude"])

                region, _ = Region.objects.get_or_create(nom=region_nom)

                cercle, _ = Cercle.objects.get_or_create(
                    region=region,
                    nom=cercle_nom
                )

                commune, _ = Commune.objects.get_or_create(
                    cercle=cercle,
                    nom=commune_nom
                )

                station = Station.objects.create(
                    nom=station_nom,
                    commune=commune,
                    latitude=latitude,
                    longitude=longitude,
                    is_approved=True,
                )

                Stock.objects.create(
                    station=station,
                    produit="essence",
                    niveau="Rupture",
                )

                Stock.objects.create(
                    station=station,
                    produit="gasoil",
                    niveau="Rupture",
                )

                created += 1

            except Exception as e:
                errors += 1
                self.stdout.write(
                    self.style.ERROR(f"Ligne {index + 2} erreur : {e}")
                )

        self.stdout.write(self.style.SUCCESS("Import terminé."))
        self.stdout.write(self.style.SUCCESS(f"Stations créées : {created}"))
        self.stdout.write(self.style.WARNING(f"Erreurs : {errors}"))