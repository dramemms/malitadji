# stations/viewsets.py
from rest_framework import viewsets
from .models import Station

class StationViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Station.objects.select_related("commune__cercle__region").all()
    serializer_class = None  # si tu n'utilises pas DRF serializers, enlève router sinon ajoute un serializer
