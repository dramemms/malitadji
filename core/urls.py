# core/urls.py
from django.contrib.auth import views as auth_views
from django.urls import path, include
from django.views.generic import TemplateView
from django.shortcuts import redirect

from stations.api_geojson import stations_geojson
from stations.admin_dashboard import admin_site

from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    # ✅ Admin Malitadji
    path("admin/", admin_site.urls),

    # --- AUTHENTIFICATION WEB ---
    path("accounts/login/", auth_views.LoginView.as_view(template_name="registration/login.html"), name="login"),
    path("accounts/logout/", auth_views.LogoutView.as_view(), name="logout"),

    # --- AUTHENTIFICATION API MOBILE (JWT) ---
    path("api/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),

    # --- API STATIONS GEOJSON ---
    path("api/stations.geojson", stations_geojson, name="stations_geojson"),
    path("api/stations.geojson/", stations_geojson),
    path("api/stations/", lambda r: redirect("/api/stations.geojson", permanent=False)),

    # --- NOTIFICATIONS ---
    path("api/notifications/", include("notifications.urls")),

    # --- PRIVACY POLICY ---
    path("privacy-policy/", TemplateView.as_view(template_name="stations/privacy-policy.html"), name="privacy_policy"),

    # ✅ APPLICATION STATIONS (gère /, /carte/, /manager/login/, etc.)
    path("", include("stations.urls")),
]
