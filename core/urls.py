from django.contrib import admin  # tu peux le laisser
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.views.generic import TemplateView

from stations.admin_dashboard import admin_site  # ✅ AJOUT

# JWT pour l'app mobile
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns = [
    # ✅ Admin Malitadji (dashboard + liste apps)
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

    # --- PRIVACY POLICY (Play Store) ---
    path(
        "privacy-policy/",
        TemplateView.as_view(template_name="stations/privacy-policy.html"),
        name="privacy_policy",
    ),

    # --- APPLICATION STATIONS ---
    path("", include("stations.urls")),
]
