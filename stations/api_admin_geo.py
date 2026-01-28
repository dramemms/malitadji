# stations/api_admin_geo.py
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.db.models import Q

from .models import Region, Cercle, Commune


def _as_int(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


@require_GET
def api_regions(request):
    """
    Retourne toutes les régions: [{id, nom}]
    """
    regions = Region.objects.all().values("id", "nom").order_by("nom")
    return JsonResponse({"results": list(regions)})


@require_GET
def api_cercles(request):
    """
    Filtrable par region_id: /api/cercles/?region_id=1
    Retourne: [{id, nom, region_id}]
    """
    region_id = _as_int(request.GET.get("region_id"))

    qs = Cercle.objects.all()
    if region_id:
        qs = qs.filter(region_id=region_id)

    cercles = qs.values("id", "nom", "region_id").order_by("nom")
    return JsonResponse({"results": list(cercles)})


@require_GET
def api_communes(request):
    """
    Filtrable par cercle_id: /api/communes/?cercle_id=10
    Retourne: [{id, nom, cercle_id}]
    """
    cercle_id = _as_int(request.GET.get("cercle_id"))

    qs = Commune.objects.all()
    if cercle_id:
        qs = qs.filter(cercle_id=cercle_id)

    communes = qs.values("id", "nom", "cercle_id").order_by("nom")
    return JsonResponse({"results": list(communes)})
