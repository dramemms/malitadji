import firebase_admin
from firebase_admin import credentials, messaging
from django.conf import settings

_app = None

def _get_app():
    global _app
    if _app:
        return _app
    cred = credentials.Certificate(str(settings.FIREBASE_SERVICE_ACCOUNT_FILE))
    _app = firebase_admin.initialize_app(cred)
    return _app

def send_push(tokens, title, body, data=None):
    if not tokens:
        return 0

    _get_app()

    msg = messaging.MulticastMessage(
        tokens=tokens,
        notification=messaging.Notification(title=title, body=body),
        data={k: str(v) for k, v in (data or {}).items()},
    )
    resp = messaging.send_each_for_multicast(msg)
    return resp.success_count
