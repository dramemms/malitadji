from django.contrib import admin
from .models import Region, Cercle, Commune, Station, Stock


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ('nom',)
    search_fields = ('nom',)


@admin.register(Cercle)
class CercleAdmin(admin.ModelAdmin):
    list_display = ('nom', 'region')
    list_filter = ('region',)
    search_fields = ('nom', 'region__nom')


@admin.register(Commune)
class CommuneAdmin(admin.ModelAdmin):
    list_display = ('nom', 'cercle', 'get_region')
    list_filter = ('cercle__region', 'cercle')
    search_fields = ('nom', 'cercle__nom', 'cercle__region__nom')

    def get_region(self, obj):
        return obj.cercle.region.nom
    get_region.short_description = "Région"


@admin.register(Station)
class StationAdmin(admin.ModelAdmin):
    list_display = ('nom', 'commune', 'get_cercle', 'get_region', 'gerant')
    list_filter = ('commune__cercle__region', 'commune', 'gerant')
    search_fields = (
        'nom',
        'adresse',
        'commune__nom',
        'commune__cercle__nom',
        'commune__cercle__region__nom',
    )

    def get_cercle(self, obj):
        return obj.commune.cercle.nom
    get_cercle.short_description = "Cercle"

    def get_region(self, obj):
        return obj.commune.cercle.region.nom
    get_region.short_description = "Région"


@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ('station', 'produit', 'niveau', 'date_maj')
    # ✅ maintenant que station → commune → cercle → région existe, ce filtre marche
    list_filter = ('produit', 'station__commune__cercle__region', 'station__commune')
    search_fields = (
        'station__nom',
        'station__commune__nom',
        'station__commune__cercle__nom',
        'station__commune__cercle__region__nom',
        'produit',
    )
