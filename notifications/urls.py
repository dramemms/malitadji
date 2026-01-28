# notifications/urls.py
from django.urls import path

from .api_test import test_push, ping

urlpatterns = [
    path("ping/", ping, name="notifications_ping"),
    path("test-push/", test_push, name="test_push"),
]
