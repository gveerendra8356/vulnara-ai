"""
active_testing/ai_verification.py

Thin wrapper connecting this module's heuristic verifiers to the Gemini
client built in Task 4 (app/triage/gemini_client.py). Deliberately does
NOT duplicate any of the Gemini call/retry/schema-validation machinery --
reuses it via run_active_test_verification_call, matching the same
structured-output + retry + backoff behavior as triage and remediation.

This is the layer that produces the final ai_verified / risk_rating that
gets written to Threat_Logs -- the heuristic functions in verifiers.py
are evidence, this function (backed by Gemini) renders the verdict.
"""

from __future__ import annotations

from app.active_testing.http_probe import ProbeResult
from app.active_testing.verifiers import HeuristicVerdict
from app.triage.gemini_client import GeminiTriageError, run_active_test_verification_call
from app.triage.prompts import build_active_test_verification_prompt
from app.triage.schemas import ActiveTestVerdict


async def ai_verify(
    attack_type: str,
    payload_used: str,
    target_url: str,
    heuristic: HeuristicVerdict,
    payload_result: ProbeResult,
) -> ActiveTestVerdict:
    """
    Calls Gemini to render a final verdict on one test attempt. If the
    Gemini call fails entirely after retries, falls back to a
    conservative, NOT-verified verdict derived from the heuristic alone
    -- we never want an AI outage to silently upgrade a finding's
    confidence, only ever to leave it appropriately uncertain.
    """
    prompt = build_active_test_verification_prompt(
        attack_type=attack_type,
        payload_used=payload_used,
        target_url=target_url,
        heuristic_signal_detected=heuristic.signal_detected,
        heuristic_reason=heuristic.reason,
        response_snippet=payload_result.body,
    )

    try:
        return await run_active_test_verification_call(prompt)
    except GeminiTriageError:
        return ActiveTestVerdict(
            ai_verified=False,
            verification_notes=(
                "AI verification unavailable (Gemini call failed after retries); "
                f"falling back to heuristic-only signal. Heuristic reason: {heuristic.reason}"
            ),
            risk_rating=heuristic.preliminary_risk_rating if heuristic.signal_detected else "INFO",
        )
