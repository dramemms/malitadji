# stations/views.py
from __future__ import annotations

from datetime import timedelta

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

import json
from django.shortcuts import render

from .models import Region, Cercle, Commune  # ✅ adapte si besoin

from .forms import StockForm
from .models import (
    DeviceFollow,
    InAppNotification,
    Station,
    StationFollow,
    Stock,
    StockHistory,
)

from notifications.utils import send_push_to_device_follows


# -----------------------------
# Helpers
# -----------------------------
def _norm_produit(p) -> str | None:
    if p is None:
        return None
    s = str(p).strip().lower()
    if not s:
        return None
    if "gaso" in s or "diesel" in s:
        return "gasoil"
    if "ess" in s or "super" in s:
        return "essence"
    return s


def _is_plein(niveau: str | None) -> bool:
    return str(niveau or "").strip().lower() == "plein"


def create_in_app_notification(*, user, station, produit: str, niveau: str) -> InAppNotification:
    title = "Carburant disponible" if _is_plein(niveau) else "Stock mis à jour"
    message = f"{station.nom} : {produit} → {niveau}"

    # Clé anti-doublon "soft" (1 notif max / minute / user / station / produit / niveau)
    minute_key = timezone.now().strftime("%Y%m%d%H%M")
    event_key = f"{user.id}:{station.id}:{produit}:{niveau}:{minute_key}"

    obj, _ = InAppNotification.objects.get_or_create(
        event_key=event_key,
        defaults={
            "user": user,
            "station": station,
            "produit": produit,
            "title": title,
            "message": message,
        },
    )
    return obj


# -----------------------------
# ✅ HOME (mise à jour intégrée)
# -----------------------------
def home(request):
    # Récupère stations + stocks en une fois (évite N+1)
    stations = Station.objects.all().prefetch_related("stocks")
    total_stations = stations.count()

    # Dernière mise à jour
    last_update = Stock.objects.order_by("-date_maj").values_list("date_maj", flat=True).first()

    # Comptage stations ayant au moins 1 stock renseigné
    stations_avec_stock = Stock.objects.values("station_id").distinct().count()

    # Status par station (priorité: rupture > faible/bas > dispo(plein) > inconnu)
    dispo_count = 0
    faible_count = 0
    rupture_count = 0
    inconnu_count = 0

    def _norm_niveau(n: str | None) -> str:
        return str(n or "").strip().lower()

    for st in stations:
        niveaux = [_norm_niveau(s.niveau) for s in st.stocks.all()]

        if not niveaux:
            inconnu_count += 1
            continue

        if any(n == "rupture" for n in niveaux):
            rupture_count += 1
        elif any(n in ("faible", "bas") for n in niveaux):
            faible_count += 1
        elif any(n == "plein" for n in niveaux):
            dispo_count += 1
        else:
            inconnu_count += 1

    # Pourcentages (évite division par zéro)
    denom = total_stations or 1

    def pct(x: int) -> int:
        return int(round((x * 100) / denom))

    ctx = {
        "total_stations": total_stations,
        "stations_avec_stock": stations_avec_stock,
        "last_update": last_update,
        "dispo_count": dispo_count,
        "faible_count": faible_count,
        "rupture_count": rupture_count,
        "inconnu_count": inconnu_count,
        "dispo_pct": pct(dispo_count),
        "faible_pct": pct(faible_count),
        "rupture_pct": pct(rupture_count),
        "inconnu_pct": pct(inconnu_count),
    }
    return render(request, "stations/home.html", ctx)


def carte(request):
    # Valeurs sélectionnées (GET)
    region_selected = (request.GET.get("region") or "").strip()
    cercle_selected = (request.GET.get("cercle") or "").strip()
    commune_selected = (request.GET.get("commune") or "").strip()
    statut_selected = (request.GET.get("statut") or "").strip()

    # Listes (pour afficher dans les <select>)
    regions = Region.objects.order_by("nom")

    cercles_qs = Cercle.objects.select_related("region").order_by("nom")
    communes_qs = Commune.objects.select_related("cercle").order_by("nom")

    # ✅ Optionnel : pré-filtrer les listes visibles selon la sélection
    cercles = cercles_qs
    communes = communes_qs

    if region_selected:
        cercles = cercles.filter(region_id=region_selected)

        # si pas de cercle choisi, on filtre les communes par région via cercle__region
        if not cercle_selected:
            communes = communes.filter(cercle__region_id=region_selected)

    if cercle_selected:
        communes = communes.filter(cercle_id=cercle_selected)

    # ✅ JSON pour ton JS (populateCercles/populateCommunes)
    cercles_json = json.dumps(list(cercles_qs.values("id", "nom", "region_id")))
    communes_json = json.dumps(list(communes_qs.values("id", "nom", "cercle_id")))

    ctx = {
        "regions": regions,
        "cercles": cercles,
        "communes": communes,

        "region_selected": region_selected,
        "cercle_selected": cercle_selected,
        "commune_selected": commune_selected,
        "statut_selected": statut_selected,

        "cercles_json": cercles_json,
        "communes_json": communes_json,
    }
    return render(request, "stations/carte.html", ctx)


# -----------------------------
# Manager auth
# -----------------------------
def manager_login(request):
    """
    Page de connexion gérant (template: stations/manager_login.html)
    - Si OK -> redirige vers /manager/
    """
    if request.user.is_authenticated:
        return redirect("/manager/")

    error = None

    if request.method == "POST":
        username = (request.POST.get("username") or "").strip()
        password = (request.POST.get("password") or "").strip()

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect("/manager/")
        error = "Identifiant ou mot de passe incorrect."

    return render(request, "stations/manager_login.html", {"error": error})


@login_required
def manager_logout(request):
    if request.method == "POST":
        logout(request)
    return redirect("/manager/")


# -----------------------------
# Manager dashboard
# -----------------------------
@login_required
def manager_dashboard(request):
    """
    Source unique:
    - POST /manager/ -> maj Stock
    - Règle push: notifier uniquement quand le niveau devient Plein (old != Plein)
    - Anti-spam: bloque répétition (station + produit + niveau) dans les 10 minutes
    """
    user = request.user
    is_super = user.is_superuser

    # -------- station resolution --------
    station_id = request.GET.get("station") or request.POST.get("station")

    if is_super:
        if station_id:
            station = get_object_or_404(Station, id=station_id)
        else:
            station = Station.objects.order_by("id").first()
            if not station:
                return render(
                    request,
                    "stations/manager_dashboard.html",
                    {
                        "message": "Aucune station dans la base.",
                        "message_error": True,
                        "is_super": is_super,
                    },
                )
    else:
        station = Station.objects.filter(gerant=user).order_by("id").first()
        if not station:
            return render(
                request,
                "stations/manager_dashboard.html",
                {
                    "message": "Aucune station assignée à ce compte gérant.",
                    "message_error": True,
                    "is_super": is_super,
                },
            )

    message = None
    message_error = False
    push_info = None

    if request.method == "POST":
        form = StockForm(request.POST)
        if form.is_valid():
            produit_raw = form.cleaned_data["produit"]  # 'essence'/'gasoil'
            niveau_new = form.cleaned_data["niveau"]  # 'Bas'/'Faible'/'Plein'/'Rupture'
            produit_norm = _norm_produit(produit_raw)

            with transaction.atomic():
                stock_obj, created = Stock.objects.select_for_update().get_or_create(
                    station=station,
                    produit=produit_raw,
                    defaults={"niveau": niveau_new},
                )
                old_niveau = None if created else stock_obj.niveau

                # Update stock
                stock_obj.niveau = niveau_new
                stock_obj.date_maj = timezone.now()
                stock_obj.save()

                # History (avec ancien/nouveau)
                StockHistory.objects.create(
                    station=station,
                    produit=produit_raw,
                    ancien_niveau=old_niveau,
                    nouveau_niveau=niveau_new,
                )

                # Règle notif
                should_notify = _is_plein(niveau_new) and not _is_plein(old_niveau)

                if should_notify:
                    # -------- Anti-spam 10 min (station + produit + niveau) --------
                    ten_min_ago = timezone.now() - timedelta(minutes=10)
                    spam_guard = InAppNotification.objects.filter(
                        station=station,
                        produit=produit_raw,
                        message__icontains=f"→ {niveau_new}",
                        created_at__gte=ten_min_ago,
                    ).exists()

                    if not spam_guard:
                        # ---- InApp (web comptes) ----
                        user_follows = (
                            StationFollow.objects.filter(station=station, is_active=True)
                            .filter(Q(produit__isnull=True) | Q(produit__iexact=produit_norm))
                            .select_related("user")
                            .distinct()
                        )
                        for follow in user_follows:
                            create_in_app_notification(
                                user=follow.user,
                                station=station,
                                produit=produit_raw,
                                niveau=niveau_new,
                            )

                        # ---- Push FCM (mobile) ----
                        device_follows = (
                            DeviceFollow.objects.filter(station=station, is_active=True)
                            .filter(Q(produit__isnull=True) | Q(produit__iexact=produit_norm))
                            .select_related("device")
                        )

                        if device_follows.exists():
                            result = send_push_to_device_follows(
                                device_follows=device_follows,
                                title="Carburant disponible",
                                body=f"{station.nom} : {produit_raw} → {niveau_new}",
                                data={
                                    "station_id": str(station.id),
                                    "produit": str(produit_norm or produit_raw),
                                    "niveau": str(niveau_new),
                                },
                            )
                            push_info = {
                                "sent": result.get("sent", 0),
                                "fail": result.get("fail", 0),
                                "token_count": result.get("token_count", 0),
                            }

                    message = f"✅ Stock enregistré : {produit_raw} → {niveau_new} (notif si abonnés)"
                else:
                    message = f"✅ Stock enregistré : {produit_raw} → {niveau_new} (pas de push)"

            return redirect(f"{request.path}?station={station.id}")

        message = "❌ Formulaire invalide."
        message_error = True
    else:
        form = StockForm()

    stocks = Stock.objects.filter(station=station).order_by("produit")
    stations_list = Station.objects.order_by("nom") if is_super else None

    return render(
        request,
        "stations/manager_dashboard.html",
        {
            "station": station,
            "stations_list": stations_list,
            "is_super": is_super,
            "form": form,
            "stocks": stocks,
            "message": message,
            "message_error": message_error,
            "push_info": push_info,
        },
    )
