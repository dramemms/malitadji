# notifications/models.py
from django.db import models
from django.utils import timezone


class DeviceToken(models.Model):
    """
    Token FCM lié à un device (device_id), pas à un user.
    """
    device_id = models.CharField(max_length=120, db_index=True)  # ex: UUID / "test-device-001"
    token = models.CharField(max_length=255, unique=True)
    platform = models.CharField(max_length=20, default="android")
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.device_id} ({self.platform})"


class PushEvent(models.Model):
    """
    Historique d'events push, pour éviter les doublons/spam.
    Exemple:
      station_id=240, produit="essence", kind="stock_alert", key="rupture"
    """
    station_id = models.IntegerField(db_index=True)
    produit = models.CharField(max_length=20, blank=True, null=True, db_index=True)  # essence/gasoil/None
    kind = models.CharField(max_length=50, db_index=True)  # ex: stock_alert
    key = models.CharField(max_length=200, db_index=True)  # ex: rupture/faible/plein/bas/...
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=["station_id", "produit", "kind", "key", "created_at"]),
        ]

    def __str__(self):
        return f"{self.kind}:{self.key} station={self.station_id} produit={self.produit} @ {self.created_at:%Y-%m-%d %H:%M}"
