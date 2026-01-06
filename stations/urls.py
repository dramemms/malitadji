from django.urls import path
from . import views

from rest_framework.routers import DefaultRouter
from .views import StationViewSet

router = DefaultRouter()
router.register(r"stations", StationViewSet, basename="stations")

urlpatterns = router.urls

urlpatterns = [
    # Page d'accueil
    path("", views.home, name="home"),

    # Carte publique
    path("carte/", views.carte, name="carte"),

    # Espace gérant
    path("manager/login/", views.manager_login, name="manager_login"),
    path("manager/logout/", views.manager_logout, name="manager_logout"),
    path("manager/", views.manager_dashboard, name="manager_dashboard"),

    # API mobile
    path("api/regions/", views.api_regions, name="api_regions"),
    path("api/cercles/", views.api_cercles, name="api_cercles"),
    path("api/communes/", views.api_communes, name="api_communes"),
    path("api/stations/", views.api_stations, name="api_stations"),
]


