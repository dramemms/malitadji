from django.urls import path, include
from . import views

from rest_framework.routers import DefaultRouter
from .views import StationViewSet

router = DefaultRouter()
router.register(r"stations", StationViewSet, basename="stations")

urlpatterns = [
    # Page d'accueil
    path("", views.home, name="home"),

    # Carte publique
    path("carte/", views.carte, name="carte"),

    # Espace gérant
    path("manager/login/", views.manager_login, name="manager_login"),
    path("manager/logout/", views.manager_logout, name="manager_logout"),
    path("manager/", views.manager_dashboard, name="manager_dashboard"),
    

    # API mobile (tes endpoints existants)
    path("api/regions/", views.api_regions, name="api_regions"),
    path("api/cercles/", views.api_cercles, name="api_cercles"),
    path("api/communes/", views.api_communes, name="api_communes"),
    path("api/stations/", views.api_stations, name="api_stations"),
path("api/device/register/", views.register_device_token, name="register_device_token"),


    # DRF router endpoints (ex: /api/stations/)
    path("api/", include(router.urls)),

    path("stations/<int:station_id>/toggle-follow/", views.toggle_follow_station, name="toggle_follow_station"),
]
