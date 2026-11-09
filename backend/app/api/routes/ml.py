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
from app.ml import risk_model, security_model
from app.models.scan import Scan
from app.models.triage_models import Vulnerability

router = APIRouter()


class RiskScoreRequest(BaseModel):
    cvss_score: float | None = None
    severity: str | None = None
    cve_id: str | None = None
    service_name: str | None = None
    service_version: str | None = None
    port: int | None = None
    confidence_score: float | None = None
    active_verified: bool = False
    internet_exposed: bool = True


@router.post("/ml/risk-score")
async def risk_score(payload: RiskScoreRequest, current_user: CurrentUser = Depends(get_current_user)):
    """Score a single finding's priority from its attributes (demo/testing)."""
    data = payload.model_dump()
    data.pop("service_version", None)  # not a priority-model feature
    feats = risk_model.features_from_finding(**data)
    result = risk_model.predict(feats)
    result["features"] = feats
    return result


def _analyze_finding(
    *, cvss_score=None, severity=None, cve_id=None, service_name=None,
    service_version=None, port=None, confidence_score=None,
    active_verified=False, internet_exposed=True,
) -> dict:
    """Runs all three trained models over one finding and returns a combined
    verdict: exploit priority, genuine-vulnerability detection, and the
    recommended patch technique. These AUGMENT (cross-check) the LLM triage."""
    priority = risk_model.predict(risk_model.features_from_finding(
        cvss_score=cvss_score, severity=severity, cve_id=cve_id,
        service_name=service_name, port=port, confidence_score=confidence_score,
        active_verified=active_verified, internet_exposed=internet_exposed,
    ))
    detection = security_model.detect(security_model.detection_features_from_finding(
        cvss_score=cvss_score, severity=severity, cve_id=cve_id,
        service_name=service_name, service_version=service_version, port=port,
        confidence_score=confidence_score, active_verified=active_verified,
    ))
    patch = security_model.recommend_patch(security_model.patch_features_from_finding(
        cvss_score=cvss_score, severity=severity, cve_id=cve_id,
        service_name=service_name, service_version=service_version,
        internet_exposed=internet_exposed,
    ))
    return {
        "priority": priority,          # logistic regression
        "detection": detection,        # logistic regression
        "patch_recommendation": patch, # decision tree
        "models": {
            "priority": "logistic_regression",
            "detection": "logistic_regression",
            "patch": "decision_tree",
        },
    }


@router.post("/ml/analyze")
async def analyze(payload: RiskScoreRequest, current_user: CurrentUser = Depends(get_current_user)):
    """Combined ML verdict for one finding: priority + detection + patch technique."""
    return _analyze_finding(**payload.model_dump())


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
        analysis = _analyze_finding(
            cvss_score=float(v.cvss_score) if v.cvss_score is not None else None,
            severity=v.severity,
            cve_id=v.cve_id,
            service_name=v.service_name,
            service_version=v.service_version,
            port=v.port,
            confidence_score=float(v.confidence_score) if v.confidence_score is not None else None,
        )
        scored.append({
            "vuln_id": str(v.vuln_id),
            "cve_id": v.cve_id,
            "severity": v.severity,
            "cvss_score": float(v.cvss_score) if v.cvss_score is not None else None,
            "host": v.host,
            "port": v.port,
            "service_name": v.service_name,
            "ml_priority_score": analysis["priority"]["priority_score"],
            "ml_priority_label": analysis["priority"]["priority_label"],
            "ml_detection_score": analysis["detection"]["detection_score"],
            "ml_is_vulnerable": analysis["detection"]["is_vulnerable"],
            "ml_patch_technique": analysis["patch_recommendation"]["technique_label"],
        })
    scored.sort(key=lambda s: s["ml_priority_score"], reverse=True)
    return {"scan_id": str(scan_id), "models": {"priority": "logistic_regression",
            "detection": "logistic_regression", "patch": "decision_tree"}, "findings": scored}
