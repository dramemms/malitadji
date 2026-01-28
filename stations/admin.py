# stations/admin.py
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.models import Group

from .admin_dashboard import admin_site  # ✅ ton admin personnalisé
from .models import (
    Region, Cercle, Commune,
    Station, Stock,
    Device, DeviceFollow,
    StationFollow, InAppNotification,
)

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

    @admin.display(description="Région")
    def get_region(self, obj):
        return obj.cercle.region.nom if obj.cercle and obj.cercle.region else ""


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

    @admin.display(description="Cercle")
    def get_cercle(self, obj):
        return obj.commune.cercle.nom if obj.commune and obj.commune.cercle else ""

    @admin.display(description="Région")
    def get_region(self, obj):
        if obj.commune and obj.commune.cercle and obj.commune.cercle.region:
            return obj.commune.cercle.region.nom
        return ""


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
# DEVICES (mobile)
# ==========================================================
@admin.register(Device, site=admin_site)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ("device_id", "platform", "is_active", "last_seen_at", "created_at")
    list_filter = ("platform", "is_active")
    search_fields = ("device_id", "fcm_token")
    readonly_fields = ("created_at", "last_seen_at")


@admin.register(DeviceFollow, site=admin_site)
class DeviceFollowAdmin(admin.ModelAdmin):
    list_display = ("device", "station", "produit", "is_active", "created_at")
    list_filter = ("produit", "is_active")
    search_fields = ("device__device_id", "station__nom")
    readonly_fields = ("created_at",)


# ==========================================================
# (Optionnel) FOLLOW / NOTIFS WEB (debug)
# ==========================================================
@admin.register(StationFollow, site=admin_site)
class StationFollowAdmin(admin.ModelAdmin):
    list_display = ("user", "station", "produit", "is_active", "created_at")
    list_filter = ("produit", "is_active")
    search_fields = ("user__username", "station__nom")
    readonly_fields = ("created_at",)


@admin.register(InAppNotification, site=admin_site)
class InAppNotificationAdmin(admin.ModelAdmin):
    list_display = ("user", "title", "station", "produit", "is_read", "created_at")
    list_filter = ("is_read", "produit")
    search_fields = ("user__username", "title", "message", "station__nom")
    readonly_fields = ("created_at",)


# ==========================================================
# USERS / GROUPS (sur ton admin_site)
# ==========================================================
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
    filter_horizontal = ("groups", "user_permissions")


@admin.register(Group, site=admin_site)
class GroupAdmin(admin.ModelAdmin):
    search_fields = ("name",)
    ordering = ("name",)
