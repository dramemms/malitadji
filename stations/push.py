# stations/push.py
import firebase_admin
from firebase_admin import credentials, messaging
from django.conf import settings

_app = None

def get_firebase_app():
    global _app
    if _app is None:
        cred = credentials.Certificate(str(settings.FIREBASE_SERVICE_ACCOUNT_FILE))
        _app = firebase_admin.initialize_app(cred)
    return _app


def send_push(tokens, title, message, data=None):
    """
    Envoie une notification FCM à plusieurs tokens.
    Compatible firebase-admin >= 6.x (dont 7.1.0).
    """
    if not tokens:
        return None

    app = get_firebase_app()

    msg = messaging.MulticastMessage(
        tokens=tokens,
        notification=messaging.Notification(title=title, body=message),
        data={k: str(v) for k, v in (data or {}).items()},
    )

    # ✅ API actuelle
    resp = messaging.send_each_for_multicast(msg, app=app)
    return resp
