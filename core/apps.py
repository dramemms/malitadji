# core/apps.py
from django.apps import AppConfig

class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"

    def ready(self):
        # Init Firebase au démarrage Django
        from .firebase import init_firebase
        try:
            init_firebase()
        except Exception as e:
            # On évite de casser tout Django si le JSON manque en dev
            print("⚠️ Firebase init error:", e)
