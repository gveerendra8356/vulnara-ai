"""
api/routes/ml.py

Exposes the trained ML **priority predictor** (see backend/ml/). It scores a
finding's exploit-likelihood from scan context, complementing the static CVSS
severity.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser, get_current_user
from app.core.db import get_session
from app.ml import risk_model
from app.models.scan import Scan
from app.models.triage_models import Vulnerability

router = APIRouter()


class RiskScoreRequest(BaseModel):
    cvss_score: float | None = None
    severity: str | None = None
    cve_id: str | None = None
    service_name: str | None = None
    port: int | None = None
    confidence_score: float | None = None
    active_verified: bool = False
    internet_exposed: bool = True


@router.post("/ml/risk-score")
async def risk_score(payload: RiskScoreRequest, current_user: CurrentUser = Depends(get_current_user)):
    """Score a single finding's priority from its attributes (demo/testing)."""
    feats = risk_model.features_from_finding(**payload.model_dump())
    result = risk_model.predict(feats)
    result["features"] = feats
    return result


@router.get("/scans/{scan_id}/risk")
async def scan_risk(
    scan_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """ML priority score for every finding in a scan (RBAC + department scoped)."""
    scan = (await session.execute(select(Scan).where(Scan.scan_id == scan_id))).scalar_one_or_none()
    if scan is None:
        raise HTTPException(status_code=404, detail="Scan not found")
    if current_user.role != "admin":
        if current_user.department_id is not None:
            allowed = scan.department_id == current_user.department_id
        else:
            allowed = scan.user_id == current_user.user_id
        if not allowed:
            raise HTTPException(status_code=403, detail="Not authorized to view this scan")

    vulns = (await session.execute(
        select(Vulnerability).where(Vulnerability.scan_id == scan_id)
    )).scalars().all()

    scored = []
    for v in vulns:
        feats = risk_model.features_from_finding(
            cvss_score=float(v.cvss_score) if v.cvss_score is not None else None,
            severity=v.severity,
            cve_id=v.cve_id,
            service_name=v.service_name,
            port=v.port,
            confidence_score=float(v.confidence_score) if v.confidence_score is not None else None,
        )
        pred = risk_model.predict(feats)
        scored.append({
            "vuln_id": str(v.vuln_id),
            "cve_id": v.cve_id,
            "severity": v.severity,
            "cvss_score": float(v.cvss_score) if v.cvss_score is not None else None,
            "host": v.host,
            "port": v.port,
            "service_name": v.service_name,
            "ml_priority_score": pred["priority_score"],
            "ml_priority_label": pred["priority_label"],
        })
    scored.sort(key=lambda s: s["ml_priority_score"], reverse=True)
    return {"scan_id": str(scan_id), "model": "logistic_regression", "findings": scored}
