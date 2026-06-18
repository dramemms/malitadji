import unicodedata

from django.core.management.base import BaseCommand
from stations.models import Station, Commune, Cercle


def clean(value):
    return str(value).strip() if value else ""


def normalize(value):
    value = clean(value).lower()
    value = unicodedata.normalize("NFKD", value)
    value = "".join(c for c in value if not unicodedata.combining(c))
    return " ".join(value.replace("-", " ").replace("'", " ").split())


ARRONDISSEMENT_MAP = {
    "commune i": "premier",
    "commune 1": "premier",
    "commune ii": "deuxieme",
    "commune 2": "deuxieme",
    "commune iii": "troisieme",
    "commune 3": "troisieme",
    "commune iv": "quatrieme",
    "commune 4": "quatrieme",
    "commune v": "cinquieme",
    "commune 5": "cinquieme",
    "commune vi": "sixieme",
    "commune 6": "sixieme",
}


class Command(BaseCommand):
    help = "Rattache les stations sans commune à partir du champ adresse"

    def handle(self, *args, **options):
        communes_by_name = {
            normalize(c.nom): c
            for c in Commune.objects.select_related("cercle", "cercle__region")
        }

        cercles_by_name = {
            normalize(c.nom): c
            for c in Cercle.objects.select_related("region")
        }

        bamako_cercles = {
            normalize(c.nom): c
            for c in Cercle.objects.select_related("region")
            if normalize(c.region.nom) == "bamako"
        }

        attached = 0
        not_attached = []

        for station in Station.objects.filter(commune__isnull=True):
            adresse = clean(station.adresse)
            parts = [clean(p) for p in adresse.split(",") if clean(p)]

            commune = None

            for part in parts:
                key = normalize(part)

                if key in communes_by_name:
                    commune = communes_by_name[key]
                    break

                if key in cercles_by_name:
                    cercle = cercles_by_name[key]
                    commune = Commune.objects.filter(cercle=cercle).order_by("nom").first()
                    break

                if key in ARRONDISSEMENT_MAP:
                    arrondissement_key = ARRONDISSEMENT_MAP[key]
                    for cercle_key, cercle in bamako_cercles.items():
                        if arrondissement_key in cercle_key:
                            commune = Commune.objects.filter(cercle=cercle).order_by("nom").first()
                            break

                if commune:
                    break

            if commune:
                station.commune = commune
                station.save(update_fields=["commune"])
                attached += 1
            else:
                not_attached.append(station)

        self.stdout.write(self.style.SUCCESS("Rattachement terminé"))
        self.stdout.write(f"Stations rattachées : {attached}")
        self.stdout.write(f"Stations non rattachées : {len(not_attached)}")

        if not_attached:
            for station in not_attached[:100]:
                self.stdout.write(f"- {station.id} | {station.nom} | {station.adresse}")