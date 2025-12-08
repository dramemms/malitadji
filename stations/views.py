# stations/views.py

from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib.auth.decorators import login_required

from .models import Region, Commune, Station, Stock, StockHistory
from .forms import StockForm


# -------------------------------------------------------------------
# Page d’accueil : redirection vers la carte
# -------------------------------------------------------------------
def home(request):
    """
    Page d'accueil simple : redirige vers la carte publique.
    """
    return redirect("carte_stations")


# -------------------------------------------------------------------
# Dashboard gérant (mise à jour des stocks)
# -------------------------------------------------------------------
@login_required
def manager_dashboard(request):
    """
    Tableau de bord de mise à jour des stocks.

    - Utilisateur normal : ne voit que les stations dont il est gérant
    - Superuser : voit toutes les stations
    """

    is_super = request.user.is_superuser

    # 1) Liste des stations accessibles
    if is_super:
        station_qs = Station.objects.select_related(
            "commune__cercle__region"
        ).order_by("nom")
    else:
        station_qs = Station.objects.filter(
            gerant=request.user
        ).select_related(
            "commune__cercle__region"
        ).order_by("nom")

    if not station_qs.exists():
        return render(
            request,
            "stations/manager_no_station.html",
            {
                "message": (
                    "Aucune station ne vous est assignée."
                    if not is_super
                    else "Aucune station n'est encore enregistrée."
                )
            },
        )

    # 2) Station sélectionnée via ?station=ID
    station_id = request.GET.get("station")
    if station_id:
        try:
            station = station_qs.get(id=station_id)
        except Station.DoesNotExist:
            station = station_qs.first()
    else:
        station = station_qs.first()

    message = None

    # 3) Traitement du POST (création / mise à jour de stock)
    if request.method == "POST":
        form = StockForm(request.POST)
        if form.is_valid():
            produit = form.cleaned_data["produit"]
            niveau = form.cleaned_data["niveau"]

            # On identifie le stock par (station, produit)
            stock_obj, created = Stock.objects.get_or_create(
                station=station,
                produit=produit,
                defaults={"niveau": niveau},
            )

            if not created:
                # Sauvegarde dans l'historique avant modification
                StockHistory.objects.create(
                    station=station,
                    produit=produit,
                    ancien_niveau=stock_obj.niveau,
                    nouveau_niveau=niveau,
                )
                stock_obj.niveau = niveau
                stock_obj.save()

            message = "Stock mis à jour avec succès."
            # Redirection pour éviter la double soumission
            url = f"{reverse('manager_dashboard')}?station={station.id}"
            return redirect(url)
    else:
        form = StockForm()

    # 4) Tous les stocks de cette station pour affichage
    stocks = Stock.objects.filter(station=station).order_by("produit")

    context = {
        "is_super": is_super,
        "stations_list": station_qs,
        "station": station,
        "stocks": stocks,
        "form": form,
        "message": message,
    }

    return render(request, "stations/manager_dashboard.html", context)


# -------------------------------------------------------------------
# Carte publique des stations
# -------------------------------------------------------------------
def carte_stations(request):
    """
    Carte publique avec filtres Région / Commune / Statut.
    Utilise le modèle Stock (produit / niveau).
    """

    region_id = request.GET.get("region")
    commune_id = request.GET.get("commune")
    statut = request.GET.get("statut")  # 'dispo', 'faible', 'rupture' ou vide

    # 1) Base : toutes les stations avec leurs relations
    stations_qs = Station.objects.select_related(
        "commune__cercle__region"
    ).prefetch_related("stocks")

    if region_id:
        stations_qs = stations_qs.filter(commune__cercle__region_id=region_id)
    if commune_id:
        stations_qs = stations_qs.filter(commune_id=commune_id)

    # Convertit le niveau (Plein / Moyen / Bas / Rupture) vers 'dispo' / 'faible' / 'rupture'
    def niveau_to_statut(niveau):
        if not niveau:
            return None
        if niveau == "Rupture":
            return "rupture"
        if niveau == "Bas":
            return "faible"
        return "dispo"  # Moyen ou Plein => disponible

    # ordre de gravité pour choisir le "pire" statut global
    order = {"rupture": 3, "faible": 2, "dispo": 1, None: 0}

    stations = []
    for st in stations_qs:
        # Dictionnaire produit -> Stock
        stocks_by_prod = {s.produit: s for s in st.stocks.all()}

        super_stock = stocks_by_prod.get("Super")
        gasoil_stock = stocks_by_prod.get("Gasoil")

        super_statut = niveau_to_statut(
            super_stock.niveau if super_stock else None
        )
        gasoil_statut = niveau_to_statut(
            gasoil_stock.niveau if gasoil_stock else None
        )

        # Attributs dynamiques pour le template
        st.super_statut = super_statut
        st.gasoil_statut = gasoil_statut

        # Dernière date de mise à jour (max des dates)
        dates = []
        if super_stock:
            dates.append(super_stock.date_maj)
        if gasoil_stock:
            dates.append(gasoil_stock.date_maj)
        st.last_update = max(dates) if dates else None

        # Statut global = le plus critique entre Super et Gasoil
        worst = None
        if super_statut or gasoil_statut:
            worst = super_statut or gasoil_statut
            if order.get(gasoil_statut, 0) > order.get(worst, 0):
                worst = gasoil_statut
        st.overall_statut = worst

        # Filtre par "statut" si demandé
        if statut:
            if worst == statut:
                stations.append(st)
        else:
            stations.append(st)

    # 3) Données pour les filtres
    regions = Region.objects.all().order_by("nom")
    communes = Commune.objects.all().order_by("nom")

    context = {
        "stations": stations,
        "regions": regions,
        "communes": communes,
        "selected_region_id": int(region_id) if region_id else None,
        "selected_commune_id": int(commune_id) if commune_id else None,
        "selected_statut": statut,
    }

    # Le template est : stations/templates/stations/carte.html
    return render(request, "stations/carte.html", context)
