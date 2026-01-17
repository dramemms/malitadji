from django.db import models
from django.contrib.auth import get_user_model

from django.utils import timezone
from django.db.models import UniqueConstraint

User = get_user_model()


# -----------------
# LOCALISATION
# -----------------

class Region(models.Model):
    nom = models.CharField(max_length=100)

    class Meta:
        ordering = ['nom']

    def __str__(self):
        return self.nom


class Cercle(models.Model):
    region = models.ForeignKey(
        Region,
        on_delete=models.CASCADE,
        related_name='cercles'
    )
    nom = models.CharField(max_length=100)

    class Meta:
        ordering = ['region__nom', 'nom']

    def __str__(self):
        return f"{self.nom} ({self.region.nom})"


class Commune(models.Model):
    cercle = models.ForeignKey(
        Cercle,
        on_delete=models.CASCADE,
        related_name='communes'
    )
    nom = models.CharField(max_length=100)

    class Meta:
        ordering = ['cercle__region__nom', 'cercle__nom', 'nom']

    def __str__(self):
        return f"{self.nom} ({self.cercle.nom}, {self.cercle.region.nom})"


# -----------------
# STATIONS
# -----------------

class Station(models.Model):
    nom = models.CharField(max_length=200)
    commune = models.ForeignKey(
        Commune,
        on_delete=models.CASCADE,
        related_name='stations'
    )
    adresse = models.CharField(max_length=255, blank=True, null=True)
    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)

    # 👤 Gérant de station
    gerant = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='stations'
    )

    class Meta:
        ordering = ['commune__cercle__region__nom', 'commune__nom', 'nom']

    def __str__(self):
        return self.nom


# -----------------
# STOCK ACTUEL
# -----------------

class Stock(models.Model):
    NIVEAUX = [
        ('Bas', 'Bas'),
        ('Faible', 'Faible'),
        ('Plein', 'Plein'),
        ('Rupture', 'Rupture'),
    ]

    PRODUITS = [
        ('essence', 'Essence'),
        ('gasoil', 'Gasoil'),
       
    ]

    station = models.ForeignKey(
        Station,
        on_delete=models.CASCADE,
        related_name='stocks'
    )
    produit = models.CharField(max_length=50, choices=PRODUITS)
    niveau = models.CharField(max_length=20, choices=NIVEAUX)
    date_maj = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date_maj']
        unique_together = ('station', 'produit')  # un stock par produit

    def __str__(self):
        return f"{self.station.nom} - {self.produit} ({self.niveau})"


# -----------------
# HISTORIQUE DU STOCK
# -----------------

class StockHistory(models.Model):
    station = models.ForeignKey(
        Station,
        on_delete=models.CASCADE,
        related_name='historique_stocks'
    )
    produit = models.CharField(max_length=50)
    ancien_niveau = models.CharField(
        max_length=20,
        blank=True,
        null=True
    )
    nouveau_niveau = models.CharField(max_length=20)
    date_maj = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date_maj']

    def __str__(self):
        return f"{self.station.nom} - {self.produit} : {self.nouveau_niveau}"



class StationFollow(models.Model):
    """
    Un utilisateur suit une station et choisit sur quel(s) produit(s) il veut être notifié.
    """
    PRODUITS = [
        ('essence', 'Essence'),
        ('gasoil', 'Gasoil'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="station_follows")
    station = models.ForeignKey(Station, on_delete=models.CASCADE, related_name="followers")

    # Si vide => on notifie pour les 2 produits (option)
    produit = models.CharField(max_length=50, choices=PRODUITS, blank=True, null=True)

    # A quel moment notifier
    notify_on_levels = models.CharField(
    max_length=50,
    choices=[
        ("Plein", "Seulement Plein"),
    ],
    default="Plein"
)


    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            UniqueConstraint(fields=["user", "station", "produit"], name="uniq_follow_user_station_product")
        ]

    def __str__(self):
        p = self.produit if self.produit else "tous"
        return f"{self.user} suit {self.station} ({p})"


class InAppNotification(models.Model):
    """
    Notification interne (web/app). Plus tard tu pourras brancher Firebase.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    station = models.ForeignKey(Station, on_delete=models.SET_NULL, null=True, blank=True)
    produit = models.CharField(max_length=50, blank=True, null=True)

    title = models.CharField(max_length=255)
    message = models.TextField()

    # Anti-doublon : un évènement unique (station+produit+niveau+minute+user)
    event_key = models.CharField(max_length=255, unique=True)

    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

class DeviceToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="device_tokens")
    token = models.CharField(max_length=255, unique=True)
    platform = models.CharField(max_length=30, default="android")  # android/web/ios
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user} ({self.platform})"
