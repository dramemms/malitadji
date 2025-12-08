from django.urls import path
from . import views

urlpatterns = [
       path("", views.home, name="home"),
    path("manager/", views.manager_dashboard, name="manager_dashboard"),
    path("carte/", views.carte_stations, name="carte_stations"),
]
