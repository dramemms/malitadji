from django.urls import path
from . import views

urlpatterns = [
    # Page d'accueil
    path("", views.home, name="home"),

    # Carte publique
    path("carte/", views.carte, name="carte"),

    # Espace gérant
    path("manager/login/", views.manager_login, name="manager_login"),
    path("manager/logout/", views.manager_logout, name="manager_logout"),
    path("manager/", views.manager_dashboard, name="manager_dashboard"),
]
