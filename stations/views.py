# stations/views.py
import json

from django.core.serializers.json import DjangoJSONEncoder
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required

from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import csrf_exempt

from django.db.models import Count
from django.utils.timezone import localtime

from rest_framework.viewsets import ReadOnlyModelViewSet

from .models import (
    Station,
    Stock,
    Region,
    Commune,
    Cercle,
    StationFollow,
)

# ⚠️ DeviceToken : selon ton projet, il est peut-être dans stations/models.py.
# Si tu n'as pas encore ce modèle, dis-le moi et je te le redonne.
from .models import DeviceToken

from .forms import StockForm
from .serializers import StationSerializer


User = get_user_model()


# ========================
# PAGE D'ACCUEIL
# ========================
def home(request):
    total_stations = Station.objects.count()
    stations_avec_stock = Station.objects.filter(stocks__isnull=False).distinct().count()

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

    dispo_count = faible_count = rupture_count = inconnu_count = 0

    last_update = (
        Stock.objects.order_by("-date_maj")
        .values_list("date_maj", flat=True)
        .first()
    )

    for s in Station.objects.all():
        essence_stock = Stock.objects.filter(station=s, produit__iexact="essence").order_by("-date_maj").first()
        gasoil_stock = Stock.objects.filter(station=s, produit__iexact="gasoil").order_by("-date_maj").first()

        essence_statut = niveau_to_code(essence_stock.niveau if essence_stock else "")
        gasoil_statut = niveau_to_code(gasoil_stock.niveau if gasoil_stock else "")

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
    region_id = request.GET.get("region") or ""
    cercle_id = request.GET.get("cercle") or ""
    commune_id = request.GET.get("commune") or ""
    statut = request.GET.get("statut") or ""

    stations_qs = Station.objects.all().select_related(
        "commune", "commune__cercle__region", "gerant"
    )

    if region_id:
        stations_qs = stations_qs.filter(commune__cercle__region_id=region_id)
    if cercle_id:
        stations_qs = stations_qs.filter(commune__cercle_id=cercle_id)
    if commune_id:
        stations_qs = stations_qs.filter(commune_id=commune_id)

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

    data = []
    for s in stations_qs:
        lat = getattr(s, "latitude", None)
        lng = getattr(s, "longitude", None)

        essence_stock = Stock.objects.filter(station=s, produit__iexact="essence").order_by("-date_maj").first()
        gasoil_stock = Stock.objects.filter(station=s, produit__iexact="gasoil").order_by("-date_maj").first()

        essence_statut = niveau_to_code(essence_stock.niveau) if essence_stock else ""
        gasoil_statut = niveau_to_code(gasoil_stock.niveau) if gasoil_stock else ""

        if statut:
            if statut == "rupture" and not (essence_statut == "rupture" or gasoil_statut == "rupture"):
                continue
            if statut == "faible" and not (essence_statut == "faible" or gasoil_statut == "faible"):
                continue
            if statut == "dispo" and not (essence_statut == "dispo" or gasoil_statut == "dispo"):
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

        dates = []
        if essence_stock and essence_stock.date_maj:
            dates.append(essence_stock.date_maj)
        if gasoil_stock and gasoil_stock.date_maj:
            dates.append(gasoil_stock.date_maj)
        last_update_iso = localtime(max(dates)).isoformat() if dates else None

        data.append({
            "id": s.id,
            "nom": s.nom,
            "lat": float(lat) if lat is not None else None,
            "lng": float(lng) if lng is not None else None,
            "region": region_name,
            "cercle": cercle_name,
            "commune": commune_name,
            "essence_statut": essence_statut,
            "gasoil_statut": gasoil_statut,
            "last_update": last_update_iso,
        })

    regions = Region.objects.all().order_by("nom")
    cercles = Cercle.objects.filter(region_id=region_id).order_by("nom") if region_id else Cercle.objects.all().order_by("nom")
    if cercle_id:
        communes = Commune.objects.filter(cercle_id=cercle_id).order_by("nom")
    elif region_id:
        communes = Commune.objects.filter(cercle__region_id=region_id).order_by("nom")
    else:
        communes = Commune.objects.all().order_by("nom")

    all_cercles = Cercle.objects.all().order_by("nom")
    all_communes = Commune.objects.all().order_by("nom")

    cercles_json = json.dumps(
        [{"id": ce.id, "nom": ce.nom, "region_id": ce.region_id} for ce in all_cercles],
        cls=DjangoJSONEncoder,
    )
    communes_json = json.dumps(
        [{"id": c.id, "nom": c.nom, "cercle_id": c.cercle_id} for c in all_communes],
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
    return carte(request)


# ========================
# CONNEXION / DÉCONNEXION GÉRANT
# ========================
def manager_login(request):
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
        error = "Nom d'utilisateur ou mot de passe incorrect."

    return render(request, "stations/manager_login.html", {"error": error})


def manager_logout(request):
    logout(request)
    return redirect("manager_login")


# ========================
# DASHBOARD GÉRANT
# ========================
@login_required(login_url="manager_login")
def manager_dashboard(request):
    user = request.user
    is_super = user.is_superuser

    station = None
    stations_list = None
    message = None

    if is_super:
        stations_list = Station.objects.all().order_by("nom")
        station_id = request.GET.get("station") or request.POST.get("station")
        station = get_object_or_404(Station, id=station_id) if station_id else stations_list.first()
        if not station:
            return render(request, "stations/manager_no_station.html", {"message": "Aucune station enregistrée."})
    else:
        station = Station.objects.filter(gerant=user).first()
        if not station:
            return render(
                request,
                "stations/manager_no_station.html",
                {"message": "Aucune station associée à ce compte. Contactez l'administrateur."},
            )

    if request.method == "POST":
        form = StockForm(request.POST)
        if form.is_valid():
            produit = form.cleaned_data["produit"]
            niveau = form.cleaned_data["niveau"]

            _, created = Stock.objects.update_or_create(
                station=station,
                produit=produit,
                defaults={"niveau": niveau},
            )
            message = "✅ Stock créé." if created else "✅ Stock mis à jour."
            form = StockForm()
        else:
            message = "❌ Erreur dans le formulaire."
    else:
        form = StockForm()

    stocks = Stock.objects.filter(station=station).order_by("-date_maj")

    return render(request, "stations/manager_dashboard.html", {
        "is_super": is_super,
        "stations_list": stations_list,
        "station": station,
        "form": form,
        "stocks": stocks,
        "message": message,
    })


# ========================
# API (MOBILE / AJAX)
# ========================
@require_GET
def api_regions(request):
    regions = Region.objects.all().order_by("nom").values("id", "nom")
    return JsonResponse(list(regions), safe=False)


@require_GET
def api_cercles(request):
    region_id = request.GET.get("region_id") or request.GET.get("region")
    qs = Cercle.objects.all().order_by("nom")
    if region_id:
        qs = qs.filter(region_id=region_id)
    return JsonResponse(list(qs.values("id", "nom", "region_id")), safe=False)


@require_GET
def api_communes(request):
    cercle_id = request.GET.get("cercle_id") or request.GET.get("cercle")
    qs = Commune.objects.all().order_by("nom")
    if cercle_id:
        qs = qs.filter(cercle_id=cercle_id)
    return JsonResponse(list(qs.values("id", "nom", "cercle_id")), safe=False)


@require_GET
def api_stations(request):
    qs = Station.objects.all().select_related("commune", "commune__cercle__region", "gerant")

    region_id = request.GET.get("region_id") or request.GET.get("region")
    cercle_id = request.GET.get("cercle_id") or request.GET.get("cercle")
    commune_id = request.GET.get("commune_id") or request.GET.get("commune")

    if region_id:
        qs = qs.filter(commune__cercle__region_id=region_id)
    if cercle_id:
        qs = qs.filter(commune__cercle_id=cercle_id)
    if commune_id:
        qs = qs.filter(commune_id=commune_id)

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

    data = []
    for s in qs[:5000]:
        essence_stock = Stock.objects.filter(station=s, produit__iexact="essence").order_by("-date_maj").first()
        gasoil_stock = Stock.objects.filter(station=s, produit__iexact="gasoil").order_by("-date_maj").first()

        essence_statut = niveau_to_code(essence_stock.niveau) if essence_stock else ""
        gasoil_statut = niveau_to_code(gasoil_stock.niveau) if gasoil_stock else ""

        maj_dates = []
        if essence_stock and essence_stock.date_maj:
            maj_dates.append(essence_stock.date_maj)
        if gasoil_stock and gasoil_stock.date_maj:
            maj_dates.append(gasoil_stock.date_maj)
        derniere_maj = max(maj_dates) if maj_dates else None

        region_name = cercle_name = commune_name = ""
        if getattr(s, "commune", None):
            commune_name = s.commune.nom
            if getattr(s.commune, "cercle", None):
                cercle_name = s.commune.cercle.nom
                if getattr(s.commune.cercle, "region", None):
                    region_name = s.commune.cercle.region.nom

        data.append({
            "id": s.id,
            "nom": s.nom,
            "adresse": getattr(s, "adresse", "") or "",
            "latitude": float(s.latitude) if s.latitude is not None else None,
            "longitude": float(s.longitude) if s.longitude is not None else None,
            "gerant": s.gerant_id,
            "region": region_name,
            "cercle": cercle_name,
            "commune": commune_name,
            "stock": {
                "essence": essence_statut,
                "gasoil": gasoil_statut,
                "derniere_maj": localtime(derniere_maj).isoformat() if derniere_maj else None,
            },
        })

    return JsonResponse(data, safe=False, json_dumps_params={"ensure_ascii": False})


class StationViewSet(ReadOnlyModelViewSet):
    queryset = Station.objects.select_related("commune__cercle__region")
    serializer_class = StationSerializer


# ========================
# DASHBOARD STAFF/ADMIN
# ========================
@staff_member_required
def malitadji_dashboard(request):
    total_stations = Station.objects.count()

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

    dispo_count = faible_count = rupture_count = inconnu_count = 0
    last_update = Stock.objects.order_by("-date_maj").values_list("date_maj", flat=True).first()

    for s in Station.objects.all():
        essence_stock = Stock.objects.filter(station=s, produit__iexact="essence").order_by("-date_maj").first()
        gasoil_stock = Stock.objects.filter(station=s, produit__iexact="gasoil").order_by("-date_maj").first()

        essence_statut = niveau_to_code(essence_stock.niveau if essence_stock else "")
        gasoil_statut = niveau_to_code(gasoil_stock.niveau if gasoil_stock else "")

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

    by_commune = (
        Station.objects.values("commune__nom")
        .annotate(n=Count("id"))
        .order_by("-n")[:10]
    )

    context = {
        "kpi": {
            "total_stations": total_stations,
            "stations_avec_stock": Station.objects.filter(stocks__isnull=False).distinct().count(),
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
        "by_commune": by_commune,
    }
    return render(request, "stations/malitadji_dashboard.html", context)


# ========================
# FOLLOW (WEB)
# ========================
@require_POST
@login_required
def toggle_follow_station(request, station_id):
    station = get_object_or_404(Station, pk=station_id)

    produit = request.POST.get("produit", "") or None
    if produit not in (None, "essence", "gasoil"):
        return JsonResponse({"ok": False, "error": "produit invalide"}, status=400)

    follow, created = StationFollow.objects.get_or_create(
        user=request.user,
        station=station,
        produit=produit,
        defaults={"is_active": True},
    )

    follow.is_active = not follow.is_active
    follow.save(update_fields=["is_active"])

    return JsonResponse({
        "ok": True,
        "followed": follow.is_active,
        "station_id": station.id,
        "produit": produit or "tous",
    })


# ========================
# 🔔 TOKEN FCM (PUBLIC pour tests)
# ========================
@csrf_exempt
@require_POST
def register_device_token(request):
    try:
        data = json.loads(request.body.decode("utf-8") or "{}")
    except Exception:
        return JsonResponse({"ok": False, "error": "JSON invalide"}, status=400)

    token = (data.get("token") or "").strip()
    platform = (data.get("platform") or "android").strip()

    if not token:
        return JsonResponse({"ok": False, "error": "token manquant"}, status=400)

    # ✅ TEMPORAIRE : rattacher au premier utilisateur
    user = User.objects.order_by("id").first()
    if not user:
        return JsonResponse({"ok": False, "error": "Aucun utilisateur en base"}, status=400)

    DeviceToken.objects.update_or_create(
        token=token,
        defaults={"user": user, "platform": platform, "is_active": True},
    )
    return JsonResponse({"ok": True})