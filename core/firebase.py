import os
import json
import firebase_admin
from firebase_admin import credentials


def init_firebase_admin() -> bool:
    # évite double init (gunicorn workers, reloads, etc.)
    if firebase_admin._apps:
        return True

    # 1) Render Secret File (recommandé)
    path = (os.getenv("FIREBASE_CREDENTIALS_PATH") or "").strip()
    if path:
        if os.path.exists(path):
            try:
                firebase_admin.initialize_app(credentials.Certificate(path))
                print("✅ Firebase Admin initialisé OK (secret file)")
                return True
            except Exception as e:
                print(f"⚠️ Firebase Admin init FAILED (secret file): {e}")
                return False
        else:
            print(f"⚠️ Firebase credentials file introuvable: {repr(path)}")

    # 2) Fallback env JSON (optionnel)
    raw = (os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON") or "").strip()
    if not raw:
        print("⚠️ Firebase Admin non initialisé: FIREBASE_CREDENTIALS_PATH invalide et FIREBASE_SERVICE_ACCOUNT_JSON absent")
        return False

    try:
        data = json.loads(raw)
        firebase_admin.initialize_app(credentials.Certificate(data))
        print("✅ Firebase Admin initialisé OK (env json)")
        return True
    except Exception as e:
        print(f"⚠️ Firebase Admin init FAILED (env json): {e}")
        return False
