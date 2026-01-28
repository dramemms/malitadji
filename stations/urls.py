# stations/urls.py
from django.urls import path
from .api_admin_geo import api_regions, api_cercles, api_communes
from . import views
from . import api

urlpatterns = [
    # Pages HTML

     path("", views.home, name="home"),        # /
    path("home/", views.home, name="home_page"),  # /home/
    path("carte/", views.carte, name="carte"),
    path("manager/login/", views.manager_login, name="manager_login"),
    path("manager/", views.manager_dashboard, name="manager_dashboard"),
    path("manager/logout/", views.manager_logout, name="manager_logout"),

    # API Device (public)
    path("api/device/register/", api.register_device, name="api_register_device"),
    path("api/device/follow/<int:station_id>/", api.follow_station, name="api_follow_station"),
    path("api/device/unfollow/<int:station_id>/", api.unfollow_station, name="api_unfollow_station"),
    path("api/device/follows/", api.my_follows, name="api_my_follows"),

    # API Geo (filtres)
    path("api/regions/", api_regions, name="api_regions"),
    path("api/cercles/", api_cercles, name="api_cercles"),
    path("api/communes/", api_communes, name="api_communes"),
]
