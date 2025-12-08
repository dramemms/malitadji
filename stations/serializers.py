from rest_framework import serializers
from .models import Station, Stock


class StockSerializer(serializers.ModelSerializer):
    class Meta:
        model = Stock
        fields = ("essence", "gasoil", "derniere_maj")


class StationSerializer(serializers.ModelSerializer):
    region = serializers.CharField(source="commune.cercle.region.nom")
    cercle = serializers.CharField(source="commune.cercle.nom")
    commune = serializers.CharField(source="commune.nom")
    stock = StockSerializer(read_only=True)

    class Meta:
        model = Station
        fields = (
            "id",
            "nom",
            "latitude",
            "longitude",
            "region",
            "cercle",
            "commune",
            "stock",
        )
