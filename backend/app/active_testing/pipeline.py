"""
active_testing/pipeline.py

Orchestrates Data Flow 3 end-to-end:
  1. HARD GATE: re-checks active_testing_enabled directly against the DB
     row (not a passed-in argument) before a single payload is sent.
  2. Discovers forms/params on the target's web-facing ports.
  3. For each target param, for each payload in the minimal catalog:
     - rate-limited (throttle + hard total-request budget)
     - sends baseline + payload request(s)
     - runs the matching heuristic verifier
     - if the heuristic finds a signal, escalates to AI verification
     - writes a Threat_Logs row regardless of verdict (even a
       not-verified attempt is useful audit trail -- "we tested this
       and found nothing" is a real, loggable result)
     - broadcasts active_test.attempt over WebSocket
  4. Called from task_runner.py / triage/pipeline.py AFTER triage
     completes, only if active_testing_enabled -- active testing runs
     against the same open web ports triage already characterized, so it
     makes sense as a later stage in the same scan, not a parallel one
     (also avoids contending for the same rate-limited target
     simultaneously with anything else this scan does).

WHY THE GATE IS RE-CHECKED HERE, NOT JUST TRUSTED FROM THE CALLER:
Task 3's Scan.active_testing_enabled is the single source of truth. This
module re-reads it from the DB rather than trusting a boolean parameter
threaded through several function calls, specifically so that "was this
scan opted in to active testing" can never silently drift from what's
actually stored -- a parameter could theoretically be set incorrectly by
a future caller; a DB re-read cannot.
"""

from __future__ import annotations

import logging
import uuid

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.active_testing.ai_verification import ai_verify
from app.active_testing.discovery import TestTarget, discover_targets
from app.active_testing.http_probe import get_baseline, send_probe
from app.active_testing.payloads import ALL_PAYLOADS, AttackType, DetectionStrategy, render
from app.active_testing.rate_limiter import ScanBudgetExceededError, ScanRequestBudget, ThrottleLimiter
from app.active_testing.verifiers import (
    verify_boolean_differential,
    verify_error_based,
    verify_executed_marker,
    verify_reflected_marker,
    verify_time_delay,
    verify_xss_execution_playwright,
)
from app.core.db import AsyncSessionLocal
from app.models.scan import Scan
from app.models.threat_log import ThreatLog
from app.websocket.manager import scan_connection_manager

logger = logging.getLogger("vulnara.active_testing.pipeline")


class ActiveTestingNotEnabledError(RuntimeError):
    """Raised (and caught internally) if the gate check fails -- should never propagate as a bug."""


async def run_active_testing(scan_id: uuid.UUID, target_urls: list[str]) -> None:
    """
    Entry point. `target_urls` are the HTTP(S) base URLs discovered from
    open ports during recon (e.g. "http://203.0.113.10:80",
    "https://203.0.113.10:443") -- the caller (task_runner.py) is
    responsible for filtering nmap's port results down to ones that look
    like web services before calling this.
    """
    scan_id_str = str(scan_id)

    async with AsyncSessionLocal() as session:
        # --------------------------------------------------------------
        # THE HARD GATE. First thing this function does with the DB.
        # --------------------------------------------------------------
        result = await session.execute(select(Scan).where(Scan.scan_id == scan_id))
        scan = result.scalar_one_or_none()

        if scan is None or not scan.active_testing_enabled:
            logger.info(
                "Active testing NOT run for scan %s -- active_testing_enabled=%s",
                scan_id_str, getattr(scan, "active_testing_enabled", None),
            )
            return  # silently a no-op, not an error -- most scans won't opt in

        logger.info("Active testing gate PASSED for scan %s -- proceeding.", scan_id_str)

    # --------------------------------------------------------------
    # Discovery
    # --------------------------------------------------------------
    all_targets: list[TestTarget] = []
    for base_url in target_urls:
        found = await discover_targets(base_url)
        all_targets.extend(found)

    if not all_targets:
        logger.info("Scan %s: active testing enabled, but no forms/params discovered.", scan_id_str)
        return

    # --------------------------------------------------------------
    # Rate limiting setup -- shared across every request this run makes.
    # --------------------------------------------------------------
    throttle = ThrottleLimiter(max_requests_per_second=1.0, jitter_seconds=0.3)
    budget = ScanRequestBudget()  # default cap from ACTIVE_TEST_MAX_REQUESTS_PER_SCAN

    async with httpx.AsyncClient(follow_redirects=True) as client:
        for target in all_targets:
            for attack_type, payload_list in ALL_PAYLOADS.items():
                for payload in payload_list:
                    try:
                        await _run_one_test(
                            session_factory=AsyncSessionLocal,
                            client=client,
                            scan_id=scan_id,
                            target=target,
                            attack_type=attack_type,
                            payload=payload,
                            throttle=throttle,
                            budget=budget,
                        )
                    except ScanBudgetExceededError as e:
                        logger.warning("Scan %s: %s", scan_id_str, e)
                        return  # stop entirely -- budget is a hard scan-wide cap


async def _run_one_test(
    session_factory,
    client: httpx.AsyncClient,
    scan_id: uuid.UUID,
    target: TestTarget,
    attack_type: AttackType,
    payload,
    throttle: ThrottleLimiter,
    budget: ScanRequestBudget,
) -> None:
    token = uuid.uuid4().hex[:12]

    # --- baseline (or two baselines, for time-based tests) ---
    if payload.detection_strategy == DetectionStrategy.TIME_DELAY:
        await budget.consume(2)
        await throttle.wait()
        baseline1 = await get_baseline(client, target)
        await throttle.wait()
        baseline2 = await get_baseline(client, target)
        baselines = [baseline1, baseline2]
        baseline = baseline1
    else:
        await budget.consume(1)
        await throttle.wait()
        baseline = await get_baseline(client, target)
        baselines = [baseline]

    # --- payload request(s) ---
    payload_value = render(payload, token)
    await budget.consume(1)
    await throttle.wait()
    payload_result = await send_probe(client, target, payload_value)

    control_result = None
    if payload.control_template:
        control_value = render(payload, token, control=True)
        await budget.consume(1)
        await throttle.wait()
        control_result = await send_probe(client, target, control_value)

    # --- heuristic verification, routed by detection strategy ---
    if payload.detection_strategy == DetectionStrategy.ERROR_SIGNATURE:
        heuristic = verify_error_based(baseline, payload_result)
    elif payload.detection_strategy == DetectionStrategy.BOOLEAN_DIFFERENTIAL:
        heuristic = verify_boolean_differential(baseline, payload_result, control_result)
    elif payload.detection_strategy == DetectionStrategy.TIME_DELAY:
        heuristic = verify_time_delay(baselines, payload_result)
    elif payload.detection_strategy == DetectionStrategy.REFLECTED_MARKER:
        heuristic = verify_reflected_marker(payload, token, payload_value, payload_result)
    elif payload.detection_strategy == DetectionStrategy.EXECUTED_MARKER:
        heuristic = verify_executed_marker(token, baseline, payload_result)
    else:
        return  # unknown strategy -- shouldn't happen, but never crash the scan over it

    # --- optional stronger XSS verification (only when a heuristic signal exists) ---
    if (
        attack_type == AttackType.XSS
        and heuristic.signal_detected
        and payload.detection_strategy == DetectionStrategy.REFLECTED_MARKER
    ):
        strong_result = await verify_xss_execution_playwright(target.url, token)
        if strong_result is not None:
            heuristic = strong_result  # real execution evidence supersedes the reflection heuristic

    # --- only escalate to AI verification (costs a Gemini call) if there's a signal to judge ---
    if heuristic.signal_detected:
        verdict = await ai_verify(
            attack_type=attack_type.value,
            payload_used=payload_value,
            target_url=target.url,
            heuristic=heuristic,
            payload_result=payload_result,
        )
    else:
        # No heuristic signal -- log a clean negative result without
        # spending a Gemini call on it. Still written to Threat_Logs:
        # "tested, found nothing" is meaningful audit trail.
        from app.triage.schemas import ActiveTestVerdict
        verdict = ActiveTestVerdict(
            ai_verified=False,
            verification_notes=heuristic.reason,
            risk_rating="INFO",
        )

    await _write_threat_log(
        session_factory=session_factory,
        scan_id=scan_id,
        target=target,
        attack_type=attack_type,
        payload_value=payload_value,
        verdict=verdict,
    )

    await scan_connection_manager.broadcast(
        str(scan_id),
        "active_test.attempt",
        {
            "attack_type": attack_type.value,
            "target_url": target.url,
            "ai_verified": verdict.ai_verified,
            "risk_rating": verdict.risk_rating,
        },
    )


async def _write_threat_log(
    session_factory,
    scan_id: uuid.UUID,
    target: TestTarget,
    attack_type: AttackType,
    payload_value: str,
    verdict,
) -> None:
    async with session_factory() as session:
        log = ThreatLog(
            scan_id=scan_id,
            vuln_id=None,  # linking to a specific Vulnerabilities row (if this
            # active-test finding corresponds to one the triage step already
            # flagged) is a reasonable enhancement but requires a matching
            # step not built here -- left null, matching the schema's
            # nullable FK, rather than guessing at a link.
            attack_type=attack_type.value,
            target_url=target.url,
            target_param=target.param_name,
            payload_used=payload_value,
            ai_verified=verdict.ai_verified,
            verification_notes=verdict.verification_notes,
            risk_rating=verdict.risk_rating,
        )
        session.add(log)
        await session.commit()
