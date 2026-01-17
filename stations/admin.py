# stations/admin.py
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.models import Group

from .models import Region, Cercle, Commune, Station, Stock
from .admin_dashboard import admin_site  # ✅ TON admin personnalisé

User = get_user_model()


# ==========================================================
# STATIONS (Region / Cercle / Commune / Station / Stock)
# ==========================================================
@admin.register(Region, site=admin_site)
class RegionAdmin(admin.ModelAdmin):
    list_display = ("nom",)
    search_fields = ("nom",)


@admin.register(Cercle, site=admin_site)
class CercleAdmin(admin.ModelAdmin):
    list_display = ("nom", "region")
    list_filter = ("region",)
    search_fields = ("nom", "region__nom")


@admin.register(Commune, site=admin_site)
class CommuneAdmin(admin.ModelAdmin):
    list_display = ("nom", "cercle", "get_region")
    list_filter = ("cercle__region", "cercle")
    search_fields = ("nom", "cercle__nom", "cercle__region__nom")

    def get_region(self, obj):
        return obj.cercle.region.nom if obj.cercle and obj.cercle.region else ""
    get_region.short_description = "Région"


@admin.register(Station, site=admin_site)
class StationAdmin(admin.ModelAdmin):
    list_display = ("nom", "commune", "get_cercle", "get_region", "gerant")
    list_filter = ("commune__cercle__region", "commune", "gerant")
    search_fields = (
        "nom",
        "adresse",
        "commune__nom",
        "commune__cercle__nom",
        "commune__cercle__region__nom",
    )

    def get_cercle(self, obj):
        return obj.commune.cercle.nom if obj.commune and obj.commune.cercle else ""
    get_cercle.short_description = "Cercle"

    def get_region(self, obj):
        if obj.commune and obj.commune.cercle and obj.commune.cercle.region:
            return obj.commune.cercle.region.nom
        return ""
    get_region.short_description = "Région"


@admin.register(Stock, site=admin_site)
class StockAdmin(admin.ModelAdmin):
    list_display = ("station", "produit", "niveau", "date_maj")
    list_filter = ("produit", "station__commune__cercle__region", "station__commune")
    search_fields = (
        "station__nom",
        "station__commune__nom",
        "station__commune__cercle__nom",
        "station__commune__cercle__region__nom",
        "produit",
    )


# ==========================================================
# USERS / GROUPS (Gestion des utilisateurs comme stations)
# ==========================================================
# (Sécurité) enlever si déjà enregistré ailleurs
try:
    admin_site.unregister(User)
except admin.sites.NotRegistered:
    pass

try:
    admin_site.unregister(Group)
except admin.sites.NotRegistered:
    pass


@admin.register(User, site=admin_site)
class UserAdmin(DjangoUserAdmin):
    """
    Admin User complet (même fonctionnalités que Django),
    mais sur ton admin_site Malitadji.
    """
    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "is_staff",
        "is_superuser",
        "is_active",
        "last_login",
    )
    list_filter = ("is_staff", "is_superuser", "is_active", "groups")
    search_fields = ("username", "email", "first_name", "last_name")
    ordering = ("username",)

    # ✅ utile pour gérer les permissions/gérants rapidement
    filter_horizontal = ("groups", "user_permissions")


@admin.register(Group, site=admin_site)
class GroupAdmin(admin.ModelAdmin):
    search_fields = ("name",)
    ordering = ("name",)
