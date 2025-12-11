import json

from django.core.serializers.json import DjangoJSONEncoder
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required

from .models import Station, Stock, Region, Commune, Cercle
from .forms import StockForm


# ========================
# PAGE D'ACCUEIL
# ========================
def home(request):
    """
    Page d'accueil publique de Malitadji :
    - descriptif du projet
    - statistiques globales
    """

    # Statistiques globales
    total_stations = Station.objects.count()

    # Stations avec au moins un stock renseigné
    stations_avec_stock = (
        Station.objects.filter(stocks__isnull=False).distinct().count()
    )

    # Convertir niveau texte -> code interne
    def niveau_to_code(niveau):
        if not niveau:
            return ""
        n = niveau.lower()
        if "rupture" in n or "out" in n:
            return "rupture"
        if "faible" in n or "low" in n:
            return "faible"
        if (
            "dispo" in n
            or "disponible" in n
            or "plein" in n
            or "full" in n
        ):
            return "dispo"
        return ""

    dispo_count = 0
    faible_count = 0
    rupture_count = 0
    inconnu_count = 0

    # Dernière date de mise à jour globale
    last_update = (
        Stock.objects.order_by("-date_maj").values_list("date_maj", flat=True).first()
    )

    # Statut global par station (Essence + Gasoil)
    for s in Station.objects.all():
        # Dernier stock ESSENCE
        essence_stock = (
            Stock.objects.filter(station=s, produit__iexact="Essence")
            .order_by("-date_maj")
            .first()
        )
        # Dernier stock GASOIL
        gasoil_stock = (
            Stock.objects.filter(station=s, produit__iexact="Gasoil")
            .order_by("-date_maj")
            .first()
        )

        essence_statut = niveau_to_code(essence_stock.niveau if essence_stock else "")
        gasoil_statut = niveau_to_code(gasoil_stock.niveau if gasoil_stock else "")

        # Logique globale : si au moins un produit est en rupture/faible/dispo
        if "rupture" in (essence_statut, gasoil_statut):
            rupture_count += 1
        elif "faible" in (essence_statut, gasoil_statut):
            faible_count += 1
        elif "dispo" in (essence_statut, gasoil_statut):
            dispo_count += 1
        else:
            inconnu_count += 1

    # Pourcentages (en évitant la division par 0)
    def pct(val):
        return round(val * 100 / total_stations, 1) if total_stations else 0

    context = {
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
    }

    return render(request, "stations/home.html", context)


# ========================
# CARTE PUBLIQUE
# ========================
def carte(request):
    """
    Alimente la carte Leaflet.

    - Filtres : région / cercle / commune / statut
    - Couleurs : calculées à partir du stock (Essence et Gasoil)
    """

    # Récupération des filtres GET
    region_id = request.GET.get("region") or ""
    cercle_id = request.GET.get("cercle") or ""
    commune_id = request.GET.get("commune") or ""
    statut = request.GET.get("statut") or ""  # dispo / faible / rupture

    # Stations + relations utiles
    stations_qs = Station.objects.all().select_related(
        "commune", "commune__cercle__region", "gerant"
    )

    # Filtres côté base de données
    if region_id:
        stations_qs = stations_qs.filter(commune__cercle__region_id=region_id)
    if cercle_id:
        stations_qs = stations_qs.filter(commune__cercle_id=cercle_id)
    if commune_id:
        stations_qs = stations_qs.filter(commune_id=commune_id)

    # Helper : convertir niveau texte -> code utilisé dans le JS
    def niveau_to_code(niveau: str | None) -> str:
        if not niveau:
            return ""
        n = niveau.lower()
        if "rupture" in n or "out" in n:
            return "rupture"
        if "faible" in n or "low" in n:
            return "faible"
        if "dispo" in n or "disponible" in n or "full" in n or "plein" in n:
            return "dispo"
        return ""

    data = []

    for s in stations_qs:
        # Coordonnées
        lat = getattr(s, "latitude", None)
        lng = getattr(s, "longitude", None)

        # Dernier stock ESSENCE
        essence_stock = (
            Stock.objects.filter(station=s, produit__iexact="Essence")
            .order_by("-date_maj")
            .first()
        )
        # Dernier stock GASOIL
        gasoil_stock = (
            Stock.objects.filter(station=s, produit__iexact="Gasoil")
            .order_by("-date_maj")
            .first()
        )

        essence_statut = niveau_to_code(essence_stock.niveau) if essence_stock else ""
        gasoil_statut = niveau_to_code(gasoil_stock.niveau) if gasoil_stock else ""

        # Filtre supplémentaire sur le statut côté Python
        if statut:
            if statut == "rupture" and not (
                essence_statut == "rupture" or gasoil_statut == "rupture"
            ):
                continue
            if statut == "faible" and not (
                essence_statut == "faible" or gasoil_statut == "faible"
            ):
                continue
            if statut == "dispo" and not (
                essence_statut == "dispo" or gasoil_statut == "dispo"
            ):
                continue

        region_name = ""
        cercle_name = ""
        commune_name = ""

        if getattr(s, "commune", None):
            commune_name = s.commune.nom
            if getattr(s.commune, "cercle", None):
                cercle_name = s.commune.cercle.nom
                if getattr(s.commune.cercle, "region", None):
                    region_name = s.commune.cercle.region.nom

        data.append(
            {
                "id": s.id,
                "nom": s.nom,
                "lat": float(lat) if lat is not None else None,
                "lng": float(lng) if lng is not None else None,
                "region": region_name,
                "cercle": cercle_name,
                "commune": commune_name,
                # on garde les clés attendues par le JS
                "super_statut": essence_statut,   # Essence
                "gasoil_statut": gasoil_statut,   # Gasoil
            }
        )

    # Listes pour les filtres (avec dépendances côté backend)
    regions = Region.objects.all().order_by("nom")

    if region_id:
        cercles = Cercle.objects.filter(region_id=region_id).order_by("nom")
    else:
        cercles = Cercle.objects.all().order_by("nom")

    if cercle_id:
        communes = Commune.objects.filter(cercle_id=cercle_id).order_by("nom")
    elif region_id:
        communes = Commune.objects.filter(cercle__region_id=region_id).order_by("nom")
    else:
        communes = Commune.objects.all().order_by("nom")

    # 🔹 Données complètes pour JS (filtres dynamiques côté client)
    all_cercles = Cercle.objects.all().order_by("nom")
    all_communes = Commune.objects.all().order_by("nom")

    cercles_json = json.dumps(
        [
            {"id": ce.id, "nom": ce.nom, "region_id": ce.region_id}
            for ce in all_cercles
        ],
        cls=DjangoJSONEncoder,
    )

    communes_json = json.dumps(
        [
            {"id": c.id, "nom": c.nom, "cercle_id": c.cercle_id}
            for c in all_communes
        ],
        cls=DjangoJSONEncoder,
    )

    context = {
        "stations_json": json.dumps(data, cls=DjangoJSONEncoder),
        "regions": regions,
        "cercles": cercles,
        "communes": communes,
        "region_selected": region_id,
        "cercle_selected": cercle_id,
        "commune_selected": commune_id,
        "statut_selected": statut,
        "cercles_json": cercles_json,
        "communes_json": communes_json,
    }

    return render(request, "stations/carte.html", context)


def carte_stations(request):
    """Alias éventuel si une ancienne URL pointe encore ici."""
    return carte(request)


# ========================
# CONNEXION / DÉCONNEXION
# ========================
def manager_login(request):
    """Page de connexion des gérants & admins."""
    if request.user.is_authenticated:
        return redirect("manager_dashboard")

    error = None

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect("manager_dashboard")
        else:
            error = "Nom d'utilisateur ou mot de passe incorrect."

    return render(request, "stations/manager_login.html", {"error": error})


def manager_logout(request):
    """Déconnexion du gérant."""
    logout(request)
    return redirect("manager_login")


# ========================
# DASHBOARD GÉRANT
# ========================
@login_required(login_url="manager_login")
def manager_dashboard(request):
    """
    Dashboard de mise à jour des stocks.

    - superuser : peut choisir n'importe quelle station
    - gérant simple : station trouvée via Station.gerant = user
    """

    user = request.user
    is_super = user.is_superuser

    station = None
    stations_list = None
    message = None

    # --- CAS SUPERUSER ---
    if is_super:
        stations_list = Station.objects.all().order_by("nom")
        station_id = request.GET.get("station") or request.POST.get("station")

        if station_id:
            station = get_object_or_404(Station, id=station_id)
        else:
            station = stations_list.first()

        if not station:
            return render(
                request,
                "stations/manager_no_station.html",
                {"message": "Aucune station enregistrée dans le système."},
            )

    # --- CAS GÉRANT SIMPLE ---
    else:
        station = Station.objects.filter(gerant=user).first()
        if not station:
            return render(
                request,
                "stations/manager_no_station.html",
                {
                    "message": (
                        "Aucune station n'est associée à ce compte utilisateur. "
                        "Contactez l'administrateur."
                    )
                },
            )

    # --- FORMULAIRE DE MISE À JOUR DU STOCK ---
    if request.method == "POST":
        form = StockForm(request.POST)
        if form.is_valid():
            produit = form.cleaned_data["produit"]
            niveau = form.cleaned_data["niveau"]

            # Met à jour ou crée un enregistrement unique (station, produit)
            stock, created = Stock.objects.update_or_create(
                station=station,
                produit=produit,
                defaults={"niveau": niveau},
            )

            if created:
                message = "✅ Stock créé avec succès."
            else:
                message = "✅ Stock mis à jour avec succès."

            form = StockForm()
        else:
            message = "❌ Erreur dans le formulaire."
    else:
        form = StockForm()

    # --- STOCKS EXISTANTS POUR LA STATION ---
    stocks = Stock.objects.filter(station=station).order_by("-date_maj")

    return render(
        request,
        "stations/manager_dashboard.html",
        {
            "is_super": is_super,
            "stations_list": stations_list,
            "station": station,
            "form": form,
            "stocks": stocks,
            "message": message,
        },
    )
