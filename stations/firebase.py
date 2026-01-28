# stations/firebase.py
import os
from django.conf import settings

import firebase_admin
from firebase_admin import credentials

def get_firebase_app():
    """
    Initialise Firebase Admin UNIQUEMENT si:
    - un fichier service account existe
    - et qu'on n'a pas déjà initialisé l'app
    Sinon, on retourne None (mode dev sans push).
    """
    if firebase_admin._apps:
        return firebase_admin.get_app()

    path = getattr(settings, "FIREBASE_SERVICE_ACCOUNT_FILE", None)
    if not path:
        return None

    path = str(path)
    if not os.path.exists(path):
        return None

    cred = credentials.Certificate(path)
    return firebase_admin.initialize_app(cred)
