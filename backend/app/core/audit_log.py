"""
core/audit_log.py

Dedicated audit trail for authorization/scope confirmations, separate from
the `Scans` table row itself.

Why log this twice (DB row + log line) instead of relying on the DB alone?
  - The Scans row can, in principle, be edited or deleted by someone with
    DB access. An append-only application log (ideally shipped to a
    write-once destination, e.g. a log aggregator or object storage
    bucket with retention lock) gives you a second, harder-to-tamper-with
    record that authorization was confirmed at a specific time, by a
    specific user, for a specific target -- which matters a lot if you
    ever need to demonstrate to a client "the system would not let this
    scan run without your sign-off."

This module intentionally does nothing clever -- it's a thin wrapper
around a dedicated named logger so you can route it independently in
your logging config (e.g. a separate file handler / higher retention)
without touching general application logs.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

audit_logger = logging.getLogger("vulnara.audit")


def log_authorization_confirmation(
    *,
    scan_id: uuid.UUID,
    user_id: uuid.UUID,
    target: str,
    justification: str,
) -> None:
    """
    Emits one structured audit log line at the moment a scan is created
    with authorization_confirmed=True. Called from the route handler,
    never from inside the background task, so the log entry's timestamp
    reflects exactly when the user attested authorization -- not when
    the scan happened to start executing.
    """
    audit_logger.info(
        "AUTHORIZATION_CONFIRMED",
        extra={
            "event": "authorization_confirmed",
            "scan_id": str(scan_id),
            "user_id": str(user_id),
            "target": target,
            "justification": justification,
            "confirmed_at": datetime.now(timezone.utc).isoformat(),
        },
    )
