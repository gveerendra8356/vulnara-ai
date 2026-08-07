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
    remediation = await generate_remediation(session, vuln_id, payload.target_os)

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
