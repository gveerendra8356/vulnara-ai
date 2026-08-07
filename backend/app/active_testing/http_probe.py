"""
active_testing/http_probe.py

Sends the actual requests: one baseline (no payload) and one payload
request per test. The baseline is not optional -- every verifier in
verifiers.py compares payload behavior AGAINST the baseline, never in
isolation. Testing without a baseline is a major false-positive source
(see FALSE_POSITIVES.md): dynamic content like timestamps, CSRF tokens,
ad slots, or "X users online" counters can make two ordinary requests
look different even with zero injection happening.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

import httpx

from app.active_testing.discovery import TestTarget

REQUEST_TIMEOUT_SECONDS = 15.0
# Generous timeout: time-based payloads intentionally add latency
# (up to ~2s in our payload set) and we need headroom above that plus
# normal network latency, without timing out and mistaking "slow" for
# "no response."

MAX_RESPONSE_BODY_CHARS = 20_000
# Cap how much response body we hold in memory / pass downstream to
# Gemini for AI verification -- full page bodies can be large and mostly
# irrelevant to the injection point.


@dataclass
class ProbeResult:
    status_code: int
    elapsed_seconds: float
    body: str  # truncated to MAX_RESPONSE_BODY_CHARS
    body_truncated: bool


async def send_probe(
    client: httpx.AsyncClient,
    target: TestTarget,
    param_value: str,
) -> ProbeResult:
    """
    Sends one request with `param_value` in `target.param_name`, all
    other fields/params held at their discovered default values.
    """
    all_params = {**target.other_params, target.param_name: param_value}

    start = time.monotonic()
    try:
        if target.method == "POST":
            resp = await client.post(target.url, data=all_params, timeout=REQUEST_TIMEOUT_SECONDS)
        else:
            resp = await client.get(target.url, params=all_params, timeout=REQUEST_TIMEOUT_SECONDS)
    except httpx.TimeoutException:
        # A timeout on a time-based payload attempt IS potentially
        # meaningful (the delay payload may have caused the server to
        # hang past our timeout) -- report it as a very long elapsed time
        # rather than swallowing it as an error, so verifiers.py can still
        # reason about it.
        elapsed = time.monotonic() - start
        return ProbeResult(status_code=0, elapsed_seconds=elapsed, body="", body_truncated=False)

    elapsed = time.monotonic() - start
    body = resp.text
    truncated = len(body) > MAX_RESPONSE_BODY_CHARS
    if truncated:
        body = body[:MAX_RESPONSE_BODY_CHARS]

    return ProbeResult(
        status_code=resp.status_code,
        elapsed_seconds=elapsed,
        body=body,
        body_truncated=truncated,
    )


async def get_baseline(client: httpx.AsyncClient, target: TestTarget, benign_value: str = "test") -> ProbeResult:
    """
    Sends the baseline (no-payload) request. Uses a benign placeholder
    value rather than an empty string, since some apps behave differently
    (e.g. validation errors) on empty required fields, which would itself
    create a false differential against payload requests.
    """
    return await send_probe(client, target, benign_value)
