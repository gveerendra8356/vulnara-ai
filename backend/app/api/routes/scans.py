"""
api/routes/scans.py

Implements:
  - POST /scans           -- the authorization gate
  - GET  /scans           -- list scans (RBAC: admin=all+attributed, analyst/client=own)
  - GET  /scans/{scan_id} -- get single scan with severity counts
  - POST /scans/{scan_id}/cancel
  - GET  /scans/{scan_id}/vulnerabilities
  - GET  /scans/{scan_id}/threat-logs
  - GET  /scans/{scan_id}/remediations
  - WSS  /ws/scans/{scan_id}
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
from app.models.triage_models import Vulnerability, Remediation, CVEDefinition
from app.models.threat_log import ThreatLog
from app.schemas.scan import ScanCreateRequest, ScanCreateResponse
from app.schemas.triage import VulnerabilityResponse, ThreatLogResponse, RemediationResponse
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
    Creates a new scan. Authorization gate: scan_confirmed must be true
    and justification non-blank before any DB write or background task.
    """
    if not payload.authorization_confirmed:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "Scan cannot be created: authorization_confirmed must be true. "
                "Vulnara only scans targets the requester owns or has explicit "
                "written permission to test."
            ),
        )

    if not payload.authorization_justification or not payload.authorization_justification.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="authorization_justification is required and cannot be blank.",
        )

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

    log_authorization_confirmation(
        scan_id=scan.scan_id,
        user_id=current_user.user_id,
        target=payload.target,
        justification=payload.authorization_justification,
    )

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


@router.get("/scans")
async def list_scans(
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    RBAC:
      admin   -> all scans with user attribution (email, name, role)
      analyst -> all scans with user attribution (triage duty spans every
                 user's targets, per the product spec -- analysts are not
                 limited to scans they personally kicked off)
      client  -> own scans only
    """
    from app.models.user import User as UserModel

    if current_user.role in ("admin", "analyst"):
        stmt = (
            select(Scan, UserModel.email, UserModel.full_name, UserModel.role)
            .join(UserModel, Scan.user_id == UserModel.user_id)
            .order_by(Scan.created_at.desc())
        )
        result = await session.execute(stmt)
        rows = result.all()
        return [
            {
                "scan_id": str(row.Scan.scan_id),
                "target": row.Scan.target,
                "status": row.Scan.status,
                "active_testing_enabled": row.Scan.active_testing_enabled,
                "started_at": row.Scan.started_at,
                "completed_at": row.Scan.completed_at,
                "created_at": row.Scan.created_at,
                "user_id": str(row.Scan.user_id),
                "user_email": row.email,
                "user_full_name": row.full_name,
                "user_role": row.role,
            }
            for row in rows
        ]
    else:
        # analyst and client: own scans only
        stmt = (
            select(Scan)
            .where(Scan.user_id == current_user.user_id)
            .order_by(Scan.created_at.desc())
        )
        result = await session.execute(stmt)
        return result.scalars().all()


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

    if scan.user_id != current_user.user_id and current_user.role not in ("admin", "analyst"):
        raise HTTPException(status_code=403, detail="Not authorized to view this scan")

    from sqlalchemy import func
    counts_result = await session.execute(
        select(Vulnerability.severity, func.count())
        .where(Vulnerability.scan_id == scan_id)
        .group_by(Vulnerability.severity)
    )
    severity_counts = dict(counts_result.all())

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
        "vuln_count_by_severity": {
            sev: severity_counts.get(sev, 0)
            for sev in ("CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO")
        },
    }


@router.post("/scans/{scan_id}/cancel")
async def cancel_scan(
    scan_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(Scan).where(Scan.scan_id == scan_id))
    scan = result.scalar_one_or_none()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    if scan.user_id != current_user.user_id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")

    if scan.status in ["PENDING", "IN_PROGRESS"]:
        scan.status = "CANCELLED"
        await session.commit()
        await session.refresh(scan)
    return scan


@router.get("/scans/{scan_id}/vulnerabilities", response_model=list[VulnerabilityResponse])
async def list_scan_vulnerabilities(
    scan_id: uuid.UUID,
    severity: str | None = None,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    scan_result = await session.execute(select(Scan).where(Scan.scan_id == scan_id))
    scan = scan_result.scalar_one_or_none()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    if scan.user_id != current_user.user_id and current_user.role not in ("admin", "analyst"):
        raise HTTPException(status_code=403, detail="Not authorized")

    stmt = select(Vulnerability).where(Vulnerability.scan_id == scan_id)
    if severity:
        severities = [s.strip().upper() for s in severity.split(",")]
        stmt = stmt.where(Vulnerability.severity.in_(severities))

    result = await session.execute(stmt.order_by(Vulnerability.discovered_at.desc()))
    return result.scalars().all()


@router.get("/scans/{scan_id}/threat-logs", response_model=list[ThreatLogResponse])
async def list_scan_threat_logs(
    scan_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    scan_result = await session.execute(select(Scan).where(Scan.scan_id == scan_id))
    scan = scan_result.scalar_one_or_none()
    if not scan or (scan.user_id != current_user.user_id and current_user.role not in ("admin", "analyst")):
        raise HTTPException(status_code=404, detail="Scan not found")

    stmt = select(ThreatLog).where(ThreatLog.scan_id == scan_id).order_by(ThreatLog.executed_at.desc())
    result = await session.execute(stmt)
    return result.scalars().all()


@router.get("/scans/{scan_id}/remediations", response_model=list[RemediationResponse])
async def list_scan_remediations(
    scan_id: uuid.UUID,
    status: str | None = None,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    scan_result = await session.execute(select(Scan).where(Scan.scan_id == scan_id))
    scan = scan_result.scalar_one_or_none()
    if not scan or (scan.user_id != current_user.user_id and current_user.role not in ("admin", "analyst")):
        raise HTTPException(status_code=404, detail="Scan not found")

    stmt = (
        select(Remediation)
        .join(Vulnerability, Remediation.vuln_id == Vulnerability.vuln_id)
        .where(Vulnerability.scan_id == scan_id)
        .order_by(Remediation.created_at.desc())
    )
    if status:
        stmt = stmt.where(Remediation.status == status.strip().upper())
    result = await session.execute(stmt)
    return result.scalars().all()


@router.websocket("/ws/scans/{scan_id}")
async def scan_status_ws(websocket: WebSocket, scan_id: uuid.UUID):
    """Live scan status stream. Token passed as query param."""
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4001)
        return

    from jose import jwt, JWTError
    from app.core.security import SECRET_KEY, ALGORITHM
    from app.models.user import User
    from app.core.db import AsyncSessionLocal

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id_str = payload.get("sub")
        if not user_id_str:
            await websocket.close(code=4001)
            return
        user_id = uuid.UUID(user_id_str)
    except JWTError:
        await websocket.close(code=4001)
        return

    async with AsyncSessionLocal() as session:
        user_result = await session.execute(select(User).where(User.user_id == user_id))
        user = user_result.scalar_one_or_none()
        if not user:
            await websocket.close(code=4001)
            return

        scan_result = await session.execute(select(Scan).where(Scan.scan_id == scan_id))
        scan = scan_result.scalar_one_or_none()
        if not scan:
            await websocket.close(code=4004)
            return

        if scan.user_id != user.user_id and user.role not in ("admin", "analyst"):
            await websocket.close(code=4003)
            return

    scan_id_str = str(scan_id)
    await scan_connection_manager.connect(scan_id_str, websocket)

    try:
        while True:
            msg = await websocket.receive_json()
            if msg.get("event") == "ping":
                await websocket.send_json({"event": "pong"})
    except WebSocketDisconnect:
        pass
    finally:
        await scan_connection_manager.disconnect(scan_id_str, websocket)
