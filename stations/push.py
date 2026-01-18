import firebase_admin
from firebase_admin import credentials, messaging
from django.conf import settings


def _get_app():
    # évite de réinitialiser firebase plusieurs fois
    if firebase_admin._apps:
        return firebase_admin.get_app()

    cred_path = str(settings.FIREBASE_SERVICE_ACCOUNT_FILE)

    cred = credentials.Certificate(cred_path)
    return firebase_admin.initialize_app(cred)


def send_push(tokens, title, body, data=None):
    if not tokens:
        return {"ok": False, "sent": 0, "error": "no_tokens"}

    _get_app()

    # Nettoyage tokens vides
    tokens = [t for t in tokens if t]
    if not tokens:
        return {"ok": False, "sent": 0, "error": "empty_tokens"}

    message = messaging.MulticastMessage(
        tokens=tokens,
        notification=messaging.Notification(title=title, body=body),
        data={k: str(v) for k, v in (data or {}).items()},
    )

    resp = messaging.send_each_for_multicast(message)

    # debug utile
    return {
        "ok": True,
        "success": resp.success_count,
        "failure": resp.failure_count,
        "responses": [
            (r.success, str(r.exception) if r.exception else None)
            for r in resp.responses
        ],
    }
