"""
remediation/remediation_service.py

Implements Task 4, item 2: given a vulnerability_id and target_os,
generates an executive summary + technical script via Gemini, and stores
the result in Remediations with status=PENDING. Matches API contract
endpoint 5.1 (POST /vulnerabilities/{vuln_id}/remediations).

Nothing in this module executes anything. It writes one row and stops --
enforcing "AI proposes, human disposes" at the code-structure level, not
just as a policy: there is no function anywhere in this file capable of
running the generated script.
"""

from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.triage_models import Remediation, Vulnerability
from app.triage.gemini_client import GeminiTriageError, run_remediation_call
from app.triage.prompts import build_remediation_prompt


async def generate_remediation(
    session: AsyncSession,
    vuln_id: uuid.UUID,
    target_os: str | None,
) -> Remediation:
    result = await session.execute(
        select(Vulnerability).where(Vulnerability.vuln_id == vuln_id)
    )
    vuln = result.scalar_one_or_none()
    if vuln is None:
        raise HTTPException(status_code=404, detail="Vulnerability not found")

    vuln_data = {
        "host": vuln.host,
        "port": vuln.port,
        "service_name": vuln.service_name,
        "service_version": vuln.service_version,
        "cve_id": vuln.cve_id,
        "severity": vuln.severity,
        "cvss_score": float(vuln.cvss_score) if vuln.cvss_score is not None else None,
        "ai_reasoning": vuln.ai_reasoning,
    }

    prompt = build_remediation_prompt(vuln_data, target_os)

    try:
        ai_response = await run_remediation_call(prompt)
    except GeminiTriageError as e:
        # Surface as a 502 (upstream/AI dependency failure) rather than a
        # generic 500 -- the frontend can distinguish "AI is unavailable,
        # try again" from an actual application bug.
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Remediation generation failed: {e}",
        )

    remediation = Remediation(
        vuln_id=vuln_id,
        target_os=target_os,
        executive_summary=ai_response.executive_summary,
        technical_script=ai_response.technical_script,
        ai_confidence=ai_response.ai_confidence,
        status="PENDING",  # ALWAYS pending -- no code path sets this to
        # APPROVED or EXECUTED here. Those transitions only happen via the
        # separate /approve, /reject, /mark-executed endpoints, which
        # require an authenticated human reviewer (see API contract 5.4-5.6).
    )
    session.add(remediation)
    await session.commit()
    await session.refresh(remediation)

    return remediation
