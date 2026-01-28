# notifications/firebase.py
import firebase_admin
from firebase_admin import credentials
from django.conf import settings

def init_firebase():
    if firebase_admin._apps:
        return
    cred = credentials.Certificate(str(settings.FIREBASE_SERVICE_ACCOUNT_FILE))
    firebase_admin.initialize_app(cred)
