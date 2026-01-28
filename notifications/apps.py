from django.apps import AppConfig
from django.conf import settings

class NotificationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "notifications"

    def ready(self):
        # Init Firebase Admin une seule fois
        try:
            import firebase_admin
            from firebase_admin import credentials

            if not firebase_admin._apps:
                cred = credentials.Certificate(str(settings.FIREBASE_SERVICE_ACCOUNT_FILE))
                firebase_admin.initialize_app(cred)
                print("✅ Firebase Admin initialisé")
        except Exception as e:
            print("⚠️ Firebase Admin non initialisé:", e)
