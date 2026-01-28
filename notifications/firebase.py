# notifications/firebase.py
import json
import os
from pathlib import Path

import firebase_admin
from firebase_admin import credentials
from django.conf import settings


def _load_service_account_dict() -> dict | None:
    # 1) via settings.FIREBASE_SERVICE_ACCOUNT_FILE
    p = getattr(settings, "FIREBASE_SERVICE_ACCOUNT_FILE", None)
    if p:
        try:
            p = Path(p)
            if p.exists():
                data = json.loads(p.read_text(encoding="utf-8"))
                # Fix private_key "\n" littéraux
                pk = data.get("private_key")
                if isinstance(pk, str) and "\\n" in pk and "\n" not in pk:
                    data["private_key"] = pk.replace("\\n", "\n")
                return data
        except Exception:
            pass

    # 2) via env FIREBASE_SERVICE_ACCOUNT_JSON (string JSON)
    raw = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON") or os.environ.get("FIREBASE_SERVICE_ACCOUNT_FILE_JSON")
    if raw:
        try:
            data = json.loads(raw)
            pk = data.get("private_key")
            if isinstance(pk, str) and "\\n" in pk and "\n" not in pk:
                data["private_key"] = pk.replace("\\n", "\n")
            return data
        except Exception:
            return None

    return None


def init_firebase() -> bool:
    """
    Initialise Firebase Admin une seule fois.
    Retourne True si OK, False sinon.
    """
    try:
        if firebase_admin._apps:
            return True

        data = _load_service_account_dict()
        if not data:
            print("Firebase: aucune config trouvée (FIREBASE_SERVICE_ACCOUNT_FILE ou _JSON)")
            return False

        cred = credentials.Certificate(data)
        firebase_admin.initialize_app(cred)
        print("✅ Firebase Admin initialisé")
        return True

    except Exception as e:
        print(f"Firebase Admin non initialisé: {e}")
        return False
