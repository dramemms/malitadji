import os
import json
import firebase_admin
from firebase_admin import credentials

def init_firebase_admin():
    if firebase_admin._apps:
        return True

    raw = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON", "").strip()
    if not raw:
        print("⚠️ FIREBASE_SERVICE_ACCOUNT_JSON manquant -> notifications désactivées")
        return False

    try:
        data = json.loads(raw)
        cred = credentials.Certificate(data)
        firebase_admin.initialize_app(cred)
        print("✅ Firebase Admin initialisé OK (env json)")
        return True
    except Exception as e:
        print(f"⚠️ Firebase Admin init FAILED: {e}")
        return False
