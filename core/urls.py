from django.contrib import admin  # tu peux le laisser
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.views.generic import TemplateView
from django.shortcuts import redirect

from stations.api_geojson import stations_geojson
from stations.admin_dashboard import admin_site  # ✅ Admin custom

# JWT pour l'app mobile
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

# ✅ HOME: redirige vers la carte
def home(request):
    return redirect("carte")  # "carte" doit exister dans stations/urls.py

urlpatterns = [
    path("", home, name="home"),

    # ✅ Admin Malitadji
    path("admin/", admin_site.urls),

    # --- AUTHENTIFICATION WEB ---
    path(
        "accounts/login/",
        auth_views.LoginView.as_view(template_name="registration/login.html"),
        name="login"
    ),
    path(
        "accounts/logout/",
        auth_views.LogoutView.as_view(),
        name="logout"
    ),

    # --- AUTHENTIFICATION API MOBILE (JWT) ---
    path("api/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),

    # --- API STATIONS GEOJSON ---
    path("api/stations.geojson", stations_geojson, name="stations_geojson"),
    path("api/stations.geojson/", stations_geojson),  # accepte aussi le slash
    path("api/stations/", lambda r: redirect("/api/stations.geojson", permanent=False)),

    # --- NOTIFICATIONS ---
    path("api/notifications/", include("notifications.urls")),

    # --- PRIVACY POLICY ---
    path(
        "privacy-policy/",
        TemplateView.as_view(template_name="stations/privacy-policy.html"),
        name="privacy_policy",
    ),

    # --- APPLICATION STATIONS ---
    path("", include("stations.urls")),
]
