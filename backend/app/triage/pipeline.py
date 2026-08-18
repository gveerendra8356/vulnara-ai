"""
triage/pipeline.py

This is the module referenced as a stub in Task 3's task_runner.py
("TRIAGE HANDOFF" comment). It's Data Flow 2 from the project spec:
normalized telemetry -> AI cross-reference against CVE data -> prioritized
threat matrix.

Flow per host:
  1. For each open port, query NVD for candidate CVEs (nvd_client)
  2. Batch all ports for that host into ONE Gemini call (prompts.py already
     batches per-host, not per-port, specifically to conserve free-tier
     rate limit budget -- see RATE_LIMITS.md)
  3. Validate Gemini's response against TriageResponse
  4. Write non-false-positive findings to Vulnerabilities
  5. Upsert any newly-seen CVEs into CVE_Definitions (organic cache growth,
     complementing the scheduled NVD sync job from Data Flow 4)
  6. Broadcast vulnerability.discovered (and alert.critical for CRITICAL
     severity) over the WebSocket, matching the Task 2 contract
  7. Once all hosts are processed, mark the scan COMPLETED with real
     severity counts
"""

from __future__ import annotations

import logging
import uuid
from collections import Counter
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import AsyncSessionLocal
from app.core.push_notifications import send_critical_alert
from app.core.email_alert import send_vulnerability_alert
from app.models.scan import Scan
from app.models.triage_models import CVEDefinition, Vulnerability
from app.models.user import User
from app.triage.gemini_client import GeminiTriageError, run_triage_call
from app.triage.nvd_client import NVDClient
from app.triage.prompts import build_triage_prompt
from app.triage.schemas import TriageFinding
from app.websocket.manager import scan_connection_manager

logger = logging.getLogger("vulnara.triage.pipeline")


async def run_triage(scan_id: uuid.UUID, normalized_payload: dict[str, Any]) -> None:
    scan_id_str = str(scan_id)
    scan_target = normalized_payload["target"]

    nvd = NVDClient()
    severity_counts: Counter[str] = Counter()

    try:
        async with AsyncSessionLocal() as session:
            # Fetch scan owner details once (email + name for email alerts)
            scan_owner_row = await session.execute(
                select(Scan.user_id, User.email, User.full_name)
                .join(User, Scan.user_id == User.user_id)
                .where(Scan.scan_id == scan_id)
            )
            owner = scan_owner_row.one_or_none()
            scan_owner_id = owner.user_id if owner else None
            scan_owner_email = owner.email if owner else None
            scan_owner_name = owner.full_name if owner else "User"

            for host_entry in normalized_payload["hosts"]:
                if not host_entry["ports"]:
                    continue  # nothing open on this host, nothing to triage

                candidate_cves = await _gather_candidates(nvd, host_entry)

                try:
                    findings = await _triage_host(scan_target, host_entry, candidate_cves)
                except GeminiTriageError:
                    logger.exception(
                        "Triage failed for scan %s host %s -- skipping this host, "
                        "continuing with the rest of the scan rather than failing "
                        "the whole scan over one host's AI call.",
                        scan_id_str, host_entry["host"],
                    )
                    continue

                for finding in findings:
                    if finding.is_false_positive:
                        continue  # explicitly filtered, per Data Flow 2 spec

                    await _persist_cve_if_new(session, finding, candidate_cves, host_entry)
                    vuln = await _write_vulnerability(session, scan_id, finding)
                    severity_counts[finding.severity] += 1

                    await scan_connection_manager.broadcast(
                        scan_id_str,
                        "vulnerability.discovered",
                        {
                            "vuln_id": str(vuln.vuln_id),
                            "severity": finding.severity,
                            "host": finding.host,
                            "port": finding.port,
                            "service_name": finding.service_name,
                            "confidence_score": finding.confidence_score,
                        },
                    )

                    if finding.severity in ("CRITICAL", "HIGH"):
                        # Email alert (best-effort, runs in thread to not block)
                        if scan_owner_email:
                            import asyncio as _asyncio
                            _asyncio.get_event_loop().run_in_executor(
                                None,
                                lambda f=finding, e=scan_owner_email, n=scan_owner_name: send_vulnerability_alert(
                                    recipient_email=e,
                                    recipient_name=n,
                                    scan_target=scan_target,
                                    scan_id=scan_id,
                                    severity=f.severity,
                                    service_name=f.service_name or "unknown",
                                    host=f.host,
                                    port=f.port,
                                    cvss_score=f.cvss_score,
                                    explanation=f.explanation,
                                )
                            )

                    if finding.severity == "CRITICAL":
                        await scan_connection_manager.broadcast(
                            scan_id_str,
                            "alert.critical",
                            {
                                "vuln_id": str(vuln.vuln_id),
                                "host": finding.host,
                                "service_name": finding.service_name,
                                "summary": finding.explanation[:200],
                            },
                        )
                        # Push notification -- covers the app-closed case
                        # that the WebSocket broadcast above can't reach.
                        # Best-effort: send_critical_alert swallows its
                        # own errors (see core/push_notifications.py) so
                        # a Firebase outage can never abort scan triage.
                        if scan_owner_id is not None:
                            await send_critical_alert(
                                session,
                                user_id=scan_owner_id,
                                scan_id=scan_id,
                                title="Critical vulnerability found",
                                body=f"{finding.service_name} on {finding.host}: "
                                     f"{finding.explanation[:120]}",
                                data={
                                    "vuln_id": str(vuln.vuln_id),
                                    "event": "alert.critical",
                                },
                            )

            await _mark_scan_completed(session, scan_id)

        await scan_connection_manager.broadcast(
            scan_id_str,
            "scan.completed",
            {
                "status": "COMPLETED",
                "vuln_count_by_severity": {
                    sev: severity_counts.get(sev, 0)
                    for sev in ("CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO")
                },
            },
        )

    finally:
        await nvd.close()


# ----------------------------------------------------------------------
async def _gather_candidates(
    nvd: NVDClient, host_entry: dict[str, Any]
) -> dict[int, list[dict[str, Any]]]:
    """Fetches NVD candidates for every open port on this host, port-keyed."""
    candidates: dict[int, list[dict[str, Any]]] = {}
    for port_info in host_entry["ports"]:
        if not port_info["service_name"]:
            candidates[port_info["port"]] = []
            continue
        cves = await nvd.search_cves(
            service_name=port_info["service_name"],
            service_version=port_info["service_version"],
        )
        candidates[port_info["port"]] = cves
    return candidates


async def _triage_host(
    scan_target: str,
    host_entry: dict[str, Any],
    candidate_cves: dict[int, list[dict[str, Any]]],
) -> list[TriageFinding]:
    prompt = build_triage_prompt(scan_target, host_entry, candidate_cves)
    response = await run_triage_call(prompt)
    return response.findings


async def _persist_cve_if_new(
    session: AsyncSession,
    finding: TriageFinding,
    candidate_cves: dict[int, list[dict[str, Any]]],
    host_entry: dict[str, Any],
) -> None:
    """
    Upserts the matched CVE into CVE_Definitions if we haven't cached it
    yet, using the raw NVD data we already fetched during candidate
    gathering (no extra API call needed).
    """
    if not finding.cve_id:
        return

    raw = next(
        (c for port_list in candidate_cves.values() for c in port_list if c["cve_id"] == finding.cve_id),
        None,
    )
    if raw is None:
        return

    stmt = pg_insert(CVEDefinition).values(
        cve_id=raw["cve_id"],
        description=raw["description"],
        cvss_v3_score=raw["cvss_v3_score"],
        severity=raw["severity"],
        published_date=raw["published_date"],
        last_modified_date=raw["last_modified_date"],
        source="NVD",
        raw_data=raw["raw_data"],
    ).on_conflict_do_nothing(index_elements=["cve_id"])

    await session.execute(stmt)


async def _write_vulnerability(
    session: AsyncSession, scan_id: uuid.UUID, finding: TriageFinding
) -> Vulnerability:
    vuln = Vulnerability(
        scan_id=scan_id,
        cve_id=finding.cve_id,
        host=finding.host,
        port=finding.port,
        service_name=finding.service_name,
        service_version=finding.service_version,
        severity=finding.severity,
        cvss_score=finding.cvss_score,
        confidence_score=finding.confidence_score,
        ai_reasoning=finding.explanation,
        status="OPEN",
    )
    session.add(vuln)
    await session.commit()
    await session.refresh(vuln)
    return vuln


async def _mark_scan_completed(session: AsyncSession, scan_id: uuid.UUID) -> None:
    from datetime import datetime, timezone

    result = await session.execute(select(Scan).where(Scan.scan_id == scan_id))
    scan = result.scalar_one()
    scan.status = "COMPLETED"
    scan.completed_at = datetime.now(timezone.utc)
    await session.commit()