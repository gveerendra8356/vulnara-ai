"""
core/push_notifications.py

Thin wrapper around the Firebase Admin SDK for sending push notifications
to a user's registered devices when a CRITICAL vulnerability is found.
Called from triage/pipeline.py at the same point `alert.critical` is
broadcast over the WebSocket (see the call site there) -- the WebSocket
event covers a client with the app open and connected; this covers the
"app is closed/backgrounded" case, which is the actual point of a push
notification.

Design choices worth calling out:

- Best-effort, never fails the scan. A Firebase error (bad credentials,
  a stale/uninstalled-app token, network hiccup) is logged and swallowed
  here -- it must never propagate up and abort AI triage for the rest of
  the scan. Losing a push notification is recoverable (the user still
  sees it in-app); losing scan results because FCM was down is not.

- Firebase Admin is initialized lazily and only once (module-level
  singleton), and does nothing if FIREBASE_CREDENTIALS_PATH isn't set --
  so the rest of the backend (and its test/import checks) keeps working
  in an environment with no Firebase project configured yet.

- Sends to every token registered for the user (a user may have a phone
  and a tablet). Individual per-token failures don't abort the batch.
"""

from __future__ import annotations

import logging
import os
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.device_token import DeviceToken

logger = logging.getLogger("vulnara.push")

_firebase_app = None
_firebase_init_attempted = False


def _get_firebase_app():
    """Lazily initializes the Firebase Admin app. Returns None (and logs
    once) if FIREBASE_CREDENTIALS_PATH isn't configured -- callers must
    treat that as "push is disabled", not an error."""
    global _firebase_app, _firebase_init_attempted

    if _firebase_app is not None:
        return _firebase_app
    if _firebase_init_attempted:
        return None
    _firebase_init_attempted = True

    cred_path = os.environ.get("FIREBASE_CREDENTIALS_PATH")
    if not cred_path:
        logger.warning(
            "FIREBASE_CREDENTIALS_PATH not set -- push notifications are "
            "disabled. Critical alerts will still reach connected clients "
            "via WebSocket, just not as a push to a closed/backgrounded app."
        )
        return None

    try:
        import firebase_admin
        from firebase_admin import credentials

        cred = credentials.Certificate(cred_path)
        _firebase_app = firebase_admin.initialize_app(cred)
        logger.info("Firebase Admin initialized for push notifications.")
    except Exception:
        logger.exception("Failed to initialize Firebase Admin -- push notifications disabled.")
        _firebase_app = None

    return _firebase_app


async def send_critical_alert(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    scan_id: uuid.UUID,
    title: str,
    body: str,
    data: dict[str, Any] | None = None,
) -> None:
    """
    Sends a push notification to every device registered to user_id.
    Swallows all errors -- see module docstring. `data` is delivered as
    the FCM data payload (string values only, per FCM's requirement) so
    the app can deep-link straight to the scan on tap.
    """
    app = _get_firebase_app()
    if app is None:
        return

    tokens_result = await session.scalars(
        select(DeviceToken.fcm_token).where(DeviceToken.user_id == user_id)
    )
    tokens = list(tokens_result)
    if not tokens:
        return

    try:
        from firebase_admin import messaging
    except Exception:
        logger.exception("firebase_admin.messaging unavailable -- skipping push.")
        return

    string_data = {"scan_id": str(scan_id), **{k: str(v) for k, v in (data or {}).items()}}

    message = messaging.MulticastMessage(
        notification=messaging.Notification(title=title, body=body),
        data=string_data,
        tokens=tokens,
        android=messaging.AndroidConfig(priority="high"),
        apns=messaging.APNSConfig(
            payload=messaging.APNSPayload(aps=messaging.Aps(sound="default"))
        ),
    )

    try:
        response = messaging.send_each_for_multicast(message)
        if response.failure_count:
            logger.warning(
                "Push notification: %d/%d deliveries failed for user %s",
                response.failure_count, len(tokens), user_id,
            )
    except Exception:
        logger.exception("Push notification send failed for user %s", user_id)
