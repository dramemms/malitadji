import json
from django.core.management.base import BaseCommand
from stations.models import Region, Cercle, Commune, Station, Stock


def map_niveau(val):
    if not val:
        return None
    v = str(val).strip().lower()
    if v in ["plein", "dispo", "disponible", "full"]:
        return "plein"
    if v in ["moyen"]:
        return "moyen"
    if v in ["bas", "faible", "low"]:
        return "faible"
    if v in ["rupture", "out"]:
        return "rupture"
    return None


class Command(BaseCommand):
    help = "Import des stations depuis un JSON (UTF-8 ou UTF-8 BOM)"

    def add_arguments(self, parser):
        parser.add_argument("json_path", type=str)

    def handle(self, *args, **options):
        path = options["json_path"]

        # Lecture JSON (gère UTF-8 avec ou sans BOM)
        with open(path, "r", encoding="utf-8-sig") as f:
            payload = json.load(f)

        stations = [
            o for o in payload
            if o.get("model", "").endswith("station")
        ]

        created = 0
        updated = 0
        skipped = 0

        for obj in stations:
            fields = obj.get("fields", {})

            nom = fields.get("nom")
            adresse = fields.get("adresse")
            latitude = fields.get("latitude")
            longitude = fields.get("longitude")

            commune_id = fields.get("commune")
            if not commune_id:
                skipped += 1
                continue

            commune = Commune.objects.filter(id=commune_id).first()
            if not commune:
                skipped += 1
                continue

            # ✅ clé UNIQUE : (nom + commune)
            station, is_created = Station.objects.update_or_create(
                nom=nom,
                commune=commune,
                defaults={
                    "adresse": adresse,
                    "latitude": latitude,
                    "longitude": longitude,
                }
            )

            if is_created:
                created += 1
            else:
                updated += 1

            essence = map_niveau(fields.get("essence_niveau"))
            gasoil = map_niveau(fields.get("gasoil_niveau"))

            if essence:
                Stock.objects.update_or_create(
                    station=station,
                    produit="essence",
                    defaults={"niveau": essence}
                )

            if gasoil:
                Stock.objects.update_or_create(
                    station=station,
                    produit="gasoil",
                    defaults={"niveau": gasoil}
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Import terminé ✔️ | Créées: {created}, MAJ: {updated}, Ignorées: {skipped}"
            )
        )
