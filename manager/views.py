from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.utils import timezone

from stations.models import Station, Stock
from stations.forms import StockForm

from notifications.stock_notifier import notifier_devices_station


@login_required
def manager_dashboard(request):
    user = request.user
    is_super = user.is_superuser

    # 1) Choix station
    station = None
    stations_list = None

    if is_super:
        stations_list = Station.objects.all().order_by("nom")
        station_id = request.GET.get("station")

        if station_id:
            station = stations_list.filter(id=station_id).first()
        if station is None and stations_list.exists():
            station = stations_list.first()
    else:
        station = Station.objects.filter(gerant=user).first()

    if station is None:
        return render(request, "manager/manager.html", {
            "message": "Aucune station associée à ce compte.",
            "is_super": is_super,
            "stations_list": stations_list,
            "station": None,
            "form": StockForm(),
            "stocks": [],
        })

    message = None

    # 2) Formulaire Stock
    if request.method == "POST":
        form = StockForm(request.POST)
        if form.is_valid():
            produit = form.cleaned_data["produit"]
            niveau = form.cleaned_data["niveau"]

            stock, created = Stock.objects.get_or_create(
                station=station,
                produit=produit,
                defaults={"niveau": niveau, "date_maj": timezone.now()},
            )

            if not created:
                stock.niveau = niveau
                stock.date_maj = timezone.now()
                stock.save()
                message = "Stock mis à jour."
            else:
                message = "Stock créé."

            # ✅ NOTIF FCM : devices qui suivent cette station
            try:
                produit_label = dict(Stock.PRODUITS).get(produit, produit)
                title = "Malitadji – Stock mis à jour"
                body = f"{station.nom}: {produit_label} → {niveau}"

                notifier_devices_station(
                    station_id=station.id,
                    produit=produit,
                    title=title,
                    body=body,
                )
            except Exception as e:
                print("⚠️ FCM erreur (ignorée):", e)

            return redirect(f"/manager/?station={station.id}")
        else:
            message = "Formulaire invalide."
    else:
        form = StockForm()

    # 3) Stocks actuels (produit est un CharField)
    stocks = Stock.objects.filter(station=station).order_by("produit")

    return render(request, "manager/manager.html", {
        "message": message,
        "is_super": is_super,
        "stations_list": stations_list,
        "station": station,
        "form": form,
        "stocks": stocks,
    })
