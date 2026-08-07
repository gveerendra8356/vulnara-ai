"""
api/routes/scans.py

Implements:
  - POST /scans           (Task 2, endpoint 2.1) -- the authorization gate
  - GET  /scans/{scan_id}  (Task 2, endpoint 2.2)
  - WSS  /ws/scans/{scan_id} (Task 2, section 7)

The authorization gate is the important part of this file: scan creation
is REJECTED before any DB write and before the background task is ever
scheduled, if authorization isn't explicitly confirmed. This is checked
here in the route handler, not just via Pydantic (see schemas/scan.py
docstring for why both layers exist).
"""

from __future__ import annotations

import asyncio
import uuid

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit_log import log_authorization_confirmation
from app.core.auth import CurrentUser, get_current_user
from app.core.db import get_session
from app.models.scan import Scan
from app.schemas.scan import ScanCreateRequest, ScanCreateResponse
from app.scanner.task_runner import run_scan_task
from app.websocket.manager import scan_connection_manager

router = APIRouter()


@router.post("/scans", response_model=ScanCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_scan(
    payload: ScanCreateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ScanCreateResponse:
    """
    Creates a new scan. This is the single, non-negotiable authorization
    gate for the whole system: no scan record is created, and no nmap
    process is ever launched, unless authorization_confirmed is explicitly
    True and a non-blank justification was provided.
    """

    # --------------------------------------------------------------
    # THE GATE. This check is deliberately the very first thing that
    # happens in this handler, before any DB session work, so there is
    # no code path that could create a Scan row ahead of this check.
    # --------------------------------------------------------------
    if not payload.authorization_confirmed:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "Scan cannot be created: authorization_confirmed must be true. "
                "Vulnara only scans targets the requester owns or has explicit "
                "written permission to test."
            ),
        )

    # Pydantic's min_length=10 + the field_validator in schemas/scan.py
    # already reject blank/whitespace-only justification, but we re-assert
    # it here too -- belt and braces on a control that's this important,
    # in case ScanCreateRequest is ever constructed some other way in
    # future code (e.g. an internal service call that bypasses the API layer).
    if not payload.authorization_justification or not payload.authorization_justification.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="authorization_justification is required and cannot be blank.",
        )

    # --------------------------------------------------------------
    # Gate passed -- now it's safe to create the record and log it.
    # --------------------------------------------------------------
    scan = Scan(
        user_id=current_user.user_id,
        target=payload.target,
        authorization_confirmed=True,
        authorization_justification=payload.authorization_justification,
        active_testing_enabled=payload.active_testing_enabled,
        status="PENDING",
    )
    session.add(scan)
    await session.commit()
    await session.refresh(scan)

    # Timestamped, structured audit log entry -- independent of the DB row,
    # see core/audit_log.py docstring for why this is logged separately.
    log_authorization_confirmation(
        scan_id=scan.scan_id,
        user_id=current_user.user_id,
        target=payload.target,
        justification=payload.authorization_justification,
    )

    # Only now, after the record exists and is logged, do we schedule the
    # actual scan work. Fire-and-forget task -- the request returns
    # immediately with scan_id while scanning continues in the background
    # and reports progress over the WebSocket endpoint.
    asyncio.create_task(
        run_scan_task(
            scan_id=scan.scan_id,
            target=scan.target,
            active_testing_enabled=scan.active_testing_enabled,
        )
    )

    return ScanCreateResponse(
        scan_id=scan.scan_id,
        target=scan.target,
        status=scan.status,
        active_testing_enabled=scan.active_testing_enabled,
        created_at=scan.created_at,
    )


@router.get("/scans/{scan_id}")
async def get_scan(
    scan_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(Scan).where(Scan.scan_id == scan_id))
    scan = result.scalar_one_or_none()

    if scan is None:
        raise HTTPException(status_code=404, detail="Scan not found")

    # Ownership check -- non-admins can only view their own scans.
    if scan.user_id != current_user.user_id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to view this scan")

    return {
        "scan_id": scan.scan_id,
        "user_id": scan.user_id,
        "target": scan.target,
        "status": scan.status,
        "active_testing_enabled": scan.active_testing_enabled,
        "authorization_justification": scan.authorization_justification,
        "started_at": scan.started_at,
        "completed_at": scan.completed_at,
        "created_at": scan.created_at,
        # Real severity counts require the Vulnerabilities table / triage
        # module, not built in this task -- zeroed placeholder for now.
        "vuln_count_by_severity": {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "INFO": 0},
    }


@router.websocket("/ws/scans/{scan_id}")
async def scan_status_ws(websocket: WebSocket, scan_id: uuid.UUID):
    """
    Live scan status stream, per the API contract section 7. Token is
    passed as a query param since not all WebSocket clients can set
    custom headers.

    NOTE: this stub accepts any non-empty token; swap in real JWT
    verification + ownership check (matching get_scan's ownership logic
    above) before this goes anywhere near production.
    """
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4001)
        return

    # TODO: verify token, resolve user, and confirm user owns scan_id
    # (or is admin) before accepting -- mirroring the check in get_scan().

    scan_id_str = str(scan_id)
    await scan_connection_manager.connect(scan_id_str, websocket)

    try:
        while True:
            # We don't expect meaningful client->server traffic besides
            # the ping/pong heartbeat defined in the API contract.
            msg = await websocket.receive_json()
            if msg.get("event") == "ping":
                await websocket.send_json({"event": "pong"})
    except WebSocketDisconnect:
        pass
    finally:
        await scan_connection_manager.disconnect(scan_id_str, websocket)
