# stations/admin_dashboard.py
from django.contrib import admin
from django.db.models import Count
from .models import Station, Stock



class MalitadjiAdminSite(admin.AdminSite):
    site_header = "MALITADJI — Administration"
    site_title = "MALITADJI Admin"
    index_title = "Tableau de bord"
    index_template = "admin/malitadji_index.html"  # ✅ template custom pour /admin/

    def index(self, request, extra_context=None):
        """
        /admin/ = Dashboard + index admin standard (apps + actions récentes)
        IMPORTANT : on appelle super().index(...) pour conserver app_list + log_entries.
        """

        # ---- KPIs ----
        total_stations = Station.objects.count()

        # Stations avec au moins un stock (ton related_name semble être "stocks" vu ton code)
        stations_avec_stock = (
            Station.objects.filter(stocks__isnull=False).distinct().count()
        )

        # Dernière mise à jour globale
        last_update = (
            Stock.objects.order_by("-date_maj")
            .values_list("date_maj", flat=True)
            .first()
        )

        # Helper : convertir niveau texte -> code interne
        def niveau_to_code(niveau):
            if not niveau:
                return ""
            n = str(niveau).lower()
            if "rupture" in n or "out" in n:
                return "rupture"
            if "faible" in n or "low" in n:
                return "faible"
            if "dispo" in n or "disponible" in n or "plein" in n or "full" in n:
                return "dispo"
            return ""

        dispo_count = 0
        faible_count = 0
        rupture_count = 0
        inconnu_count = 0

        # Statut global par station (ESSENCE + GASOIL)
        for s in Station.objects.all():
            essence_stock = (
                Stock.objects.filter(station=s, produit__iexact="essence")
                .order_by("-date_maj")
                .first()
            )
            gasoil_stock = (
                Stock.objects.filter(station=s, produit__iexact="gasoil")
                .order_by("-date_maj")
                .first()
            )

            essence_statut = niveau_to_code(essence_stock.niveau) if essence_stock else ""
            gasoil_statut = niveau_to_code(gasoil_stock.niveau) if gasoil_stock else ""

            if "rupture" in (essence_statut, gasoil_statut):
                rupture_count += 1
            elif "faible" in (essence_statut, gasoil_statut):
                faible_count += 1
            elif "dispo" in (essence_statut, gasoil_statut):
                dispo_count += 1
            else:
                inconnu_count += 1

        def pct(val):
            return round(val * 100 / total_stations, 1) if total_stations else 0

        # Top communes (stations)
        by_commune = (
            Station.objects.values("commune__nom")
            .annotate(n=Count("id"))
            .order_by("-n")[:10]
        )

        dashboard_context = {
            "kpi": {
                "total_stations": total_stations,
                "stations_avec_stock": stations_avec_stock,
                "dispo_count": dispo_count,
                "faible_count": faible_count,
                "rupture_count": rupture_count,
                "inconnu_count": inconnu_count,
                "dispo_pct": pct(dispo_count),
                "faible_pct": pct(faible_count),
                "rupture_pct": pct(rupture_count),
                "inconnu_pct": pct(inconnu_count),
                "last_update": last_update,
            },
            "by_commune": list(by_commune),
        }

        if extra_context:
            dashboard_context.update(extra_context)

        # ✅ IMPORTANT : garde app_list et log_entries de Django admin
        return super().index(request, extra_context=dashboard_context)


# ✅ Instance unique à importer partout (admin.py et urls.py)
admin_site = MalitadjiAdminSite(name="malitadji_admin")
