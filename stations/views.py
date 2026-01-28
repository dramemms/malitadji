# stations/views.py
from __future__ import annotations

from datetime import timedelta

from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from .forms import StockForm
from .models import (
    Station,
    Stock,
    StockHistory,
    StationFollow,
    InAppNotification,
    DeviceFollow,
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
# Public page
# -----------------------------
def carte(request):
    return render(request, "stations/carte.html")


# -----------------------------
# Manager auth
# -----------------------------
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
                return render(request, "stations/manager_dashboard.html", {
                    "message": "Aucune station dans la base.",
                    "message_error": True,
                    "is_super": is_super,
                })
    else:
        station = Station.objects.filter(gerant=user).order_by("id").first()
        if not station:
            return render(request, "stations/manager_dashboard.html", {
                "message": "Aucune station assignée à ce compte gérant.",
                "message_error": True,
                "is_super": is_super,
            })

    message = None
    message_error = False
    push_info = None

    if request.method == "POST":
        form = StockForm(request.POST)
        if form.is_valid():
            produit_raw = form.cleaned_data["produit"]   # 'essence'/'gasoil'
            niveau_new = form.cleaned_data["niveau"]     # 'Bas'/'Faible'/'Plein'/'Rupture'
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
                            StationFollow.objects
                            .filter(station=station, is_active=True)
                            .filter(Q(produit__isnull=True) | Q(produit__iexact=produit_norm))
                            .select_related("user")
                            .distinct()
                        )
                        for follow in user_follows:
                            # notify_on_levels = "Plein" chez toi => OK
                            create_in_app_notification(
                                user=follow.user,
                                station=station,
                                produit=produit_raw,
                                niveau=niveau_new,
                            )

                        # ---- Push FCM (mobile) ----
                        device_follows = (
                            DeviceFollow.objects
                            .filter(station=station, is_active=True)
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

    return render(request, "stations/manager_dashboard.html", {
        "station": station,
        "stations_list": stations_list,
        "is_super": is_super,
        "form": form,
        "stocks": stocks,
        "message": message,
        "message_error": message_error,
        "push_info": push_info,
    })
