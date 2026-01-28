from firebase_admin import messaging
from .firebase import init_firebase

def envoyer_notif_stock(tokens: list[str], title: str, body: str, data: dict | None = None):
    init_firebase()  # ✅ garantit l’init même si ready() ne tourne pas

    tokens = [t for t in tokens if t]
    if not tokens:
        return {"ok": False, "reason": "no_tokens"}

    tokens = tokens[:500]

    msg = messaging.MulticastMessage(
        tokens=tokens,
        notification=messaging.Notification(title=title, body=body),
        data={k: str(v) for k, v in (data or {}).items()},
    )

    resp = messaging.send_each_for_multicast(msg)

    failed = []
    for i, r in enumerate(resp.responses):
        if not r.success:
            failed.append({"token": tokens[i], "error": str(r.exception)})

    return {"ok": True, "success": resp.success_count, "failure": resp.failure_count, "failed": failed[:10]}
