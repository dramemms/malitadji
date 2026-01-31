# core/apps.py
from django.apps import AppConfig

class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"

    def ready(self):
        # Init Firebase au démarrage Django
        try:
            from .firebase import init_firebase_admin
            init_firebase_admin()
        except Exception as e:
            # Ne pas casser Django si Firebase n'est pas dispo (dev / config)
            print("⚠️ Firebase init error:", e)
