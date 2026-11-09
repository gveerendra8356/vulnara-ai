"""
api/routes/remediations.py

Implements API contract endpoint 5.1: POST /vulnerabilities/{vuln_id}/remediations
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.core.auth import CurrentUser, get_current_user
from app.core.db import get_session
from app.core.config import get_config_value
from app.core.ownership import get_visible_vulnerability
from app.remediation.remediation_service import generate_remediation

router = APIRouter()


class RemediationRequest(BaseModel):
    target_os: str | None = None


@router.post("/vulnerabilities/{vuln_id}/remediations", status_code=201)
async def create_remediation(
    vuln_id: uuid.UUID,
    payload: RemediationRequest,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    vuln = await get_visible_vulnerability(session, vuln_id, current_user)
    if await get_config_value(session, "ai_remediation_enabled") != "true":
        raise HTTPException(status_code=503, detail="AI remediation is disabled")
    remediation = await generate_remediation(session, vuln, payload.target_os)

    return {
        "remediation_id": remediation.remediation_id,
        "vuln_id": remediation.vuln_id,
        "target_os": remediation.target_os,
        "executive_summary": remediation.executive_summary,
        "technical_script": remediation.technical_script,
        "ai_confidence": float(remediation.ai_confidence),
        "status": remediation.status,
        "created_at": remediation.created_at,
    }

from fastapi import HTTPException
from sqlalchemy import select
from datetime import datetime, timezone
from app.models.scan import Scan
from app.models.triage_models import Remediation, Vulnerability
from app.schemas.triage import RemediationResponse, RemediationRejectRequest

# Department / ownership scoping for remediations, mirroring the scan scope
# in api/routes/scans.py (_scan_scope_condition):
#
#   • admin                      -> sees every remediation (no restriction)
#   • analyst with a department  -> only remediations whose underlying scan
#                                   belongs to that department
#   • analyst without department -> only remediations on their own scans
#
# A remediation is linked to a scan transitively: Remediation.vuln_id ->
# Vulnerability.scan_id -> Scan. We restrict to the set of vulnerabilities
# that belong to in-scope scans via an IN-subquery, which works equally for
# the list query and single-row lookups (get / approve / reject / execute).
def _scope_to_own_scans(stmt, current_user: CurrentUser):
    if current_user.role == "admin":
        return stmt

    if current_user.department_id is not None:
        scan_cond = Scan.department_id == current_user.department_id
    else:
        scan_cond = Scan.user_id == current_user.user_id

    visible_vuln_ids = (
        select(Vulnerability.vuln_id)
        .join(Scan, Vulnerability.scan_id == Scan.scan_id)
        .where(scan_cond)
    )
    return stmt.where(Remediation.vuln_id.in_(visible_vuln_ids))


@router.get("/remediations", response_model=list[RemediationResponse])
async def list_remediations(
    status: str | None = None,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    stmt = select(Remediation).order_by(Remediation.created_at.desc())
    stmt = _scope_to_own_scans(stmt, current_user)
    if status:
        stmt = stmt.where(Remediation.status == status.strip().upper())
    result = await session.execute(stmt)
    return result.scalars().all()

@router.get("/remediations/{rem_id}", response_model=RemediationResponse)
async def get_remediation(
    rem_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    stmt = _scope_to_own_scans(
        select(Remediation).where(Remediation.remediation_id == rem_id), current_user
    )
    result = await session.execute(stmt)
    rem = result.scalar_one_or_none()
    if not rem:
        raise HTTPException(status_code=404, detail="Remediation not found")
    return rem

@router.post("/remediations/{rem_id}/approve", response_model=RemediationResponse)
async def approve_remediation(
    rem_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    if current_user.role not in ["analyst", "admin"]:
        raise HTTPException(status_code=403, detail="Not authorized")

    result = await session.execute(
        _scope_to_own_scans(
            select(Remediation).where(Remediation.remediation_id == rem_id),
            current_user,
        )
    )
    rem = result.scalar_one_or_none()
    if not rem:
        raise HTTPException(status_code=404, detail="Remediation not found")
    if rem.status != "PENDING":
        raise HTTPException(status_code=409, detail="Only pending remediations can be approved")

    rem.status = "APPROVED"
    rem.reviewed_by = current_user.user_id
    rem.reviewed_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(rem)
    return rem

@router.post("/remediations/{rem_id}/reject", response_model=RemediationResponse)
async def reject_remediation(
    rem_id: uuid.UUID,
    payload: RemediationRejectRequest,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    if current_user.role not in ["analyst", "admin"]:
        raise HTTPException(status_code=403, detail="Not authorized")

    result = await session.execute(
        _scope_to_own_scans(
            select(Remediation).where(Remediation.remediation_id == rem_id),
            current_user,
        )
    )
    rem = result.scalar_one_or_none()
    if not rem:
        raise HTTPException(status_code=404, detail="Remediation not found")
    if rem.status != "PENDING":
        raise HTTPException(status_code=409, detail="Only pending remediations can be rejected")

    rem.status = "REJECTED"
    rem.reviewed_by = current_user.user_id
    rem.reviewed_at = datetime.now(timezone.utc)
    # in a full implementation we'd log the payload.reason
    await session.commit()
    await session.refresh(rem)
    return rem

@router.post("/remediations/{rem_id}/mark-executed", response_model=RemediationResponse)
async def mark_remediation_executed(
    rem_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    if current_user.role not in ["analyst", "admin"]:
        raise HTTPException(status_code=403, detail="Not authorized")

    stmt = _scope_to_own_scans(
        select(Remediation).where(Remediation.remediation_id == rem_id), current_user
    )
    result = await session.execute(stmt)
    rem = result.scalar_one_or_none()
    if not rem:
        raise HTTPException(status_code=404, detail="Remediation not found")

    if rem.status != "APPROVED":
        raise HTTPException(status_code=400, detail="Remediation must be approved before execution")
        
    rem.status = "EXECUTED"
    rem.executed_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(rem)
    return rem
