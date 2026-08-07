from __future__ import annotations

import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser, get_current_user
from app.core.db import get_session
from app.models.triage_models import Vulnerability
from app.schemas.triage import VulnerabilityResponse, VulnerabilityUpdateRequest

router = APIRouter()

@router.get("/vulnerabilities/{vuln_id}", response_model=VulnerabilityResponse)
async def get_vulnerability(
    vuln_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(Vulnerability).where(Vulnerability.vuln_id == vuln_id))
    vuln = result.scalar_one_or_none()
    
    if not vuln:
        raise HTTPException(status_code=404, detail="Vulnerability not found")
        
    return vuln

@router.patch("/vulnerabilities/{vuln_id}", response_model=VulnerabilityResponse)
async def update_vulnerability(
    vuln_id: uuid.UUID,
    payload: VulnerabilityUpdateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    # Only analysts and admins can update a vulnerability
    if current_user.role not in ["analyst", "admin"]:
        raise HTTPException(status_code=403, detail="Not authorized")

    result = await session.execute(select(Vulnerability).where(Vulnerability.vuln_id == vuln_id))
    vuln = result.scalar_one_or_none()
    
    if not vuln:
        raise HTTPException(status_code=404, detail="Vulnerability not found")
        
    vuln.status = payload.status
    await session.commit()
    await session.refresh(vuln)
    
    return vuln
