"""
active_testing/verifiers.py

THIS IS THE MODULE THAT ANSWERS "reflected vs. actually executed."

Important framing up front: the heuristics in this file produce a
SIGNAL, not a verdict. Every function here returns a HeuristicVerdict
with signal_detected (bool) + a reason string + a preliminary risk
rating -- this is deliberately the INPUT to AI verification
(ai_verification.py), not the final answer. Per your architecture spec
("AI verifies actual reflection/execution -- not just pattern match"),
the AI layer is what makes the final call, using these heuristics plus
the raw response context as evidence. Naive string-matching alone
(e.g. "the payload string appears in the response") is exactly the
false-positive-prone approach your spec explicitly asks NOT to rely on
-- it doesn't distinguish "the app reflected my <script> tag unescaped"
from "the app HTML-encoded it as &lt;script&gt; and it's sitting there
completely inert."

Each verifier function is annotated with its specific false-positive/
false-negative risks -- collected together in FALSE_POSITIVES.md for
your thesis limitations section.
"""

from __future__ import annotations

import difflib
import re
import statistics
from dataclasses import dataclass

from app.active_testing.http_probe import ProbeResult
from app.active_testing.payloads import DetectionStrategy, Payload

RiskRating = str  # "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "INFO"


@dataclass
class HeuristicVerdict:
    signal_detected: bool
    reason: str
    preliminary_risk_rating: RiskRating


# ----------------------------------------------------------------------
# SQLi: error-based
# ----------------------------------------------------------------------
_DB_ERROR_SIGNATURES = [
    # A deliberately small, well-known set -- not exhaustive. Real DB
    # error message wording changes across versions/config, so this will
    # miss custom or localized error pages entirely (false negative).
    r"you have an error in your sql syntax",           # MySQL
    r"warning: mysql_",                                  # MySQL (old PHP driver)
    r"unclosed quotation mark after the character string",  # MSSQL
    r"quoted string not properly terminated",           # Oracle
    r"pg_query\(\)",                                     # PostgreSQL (PHP driver)
    r"psycopg2\.",                                       # PostgreSQL (Python driver)
    r"sqlite3\.OperationalError",                        # SQLite
    r"ORA-\d{5}",                                         # Oracle error codes
]
_DB_ERROR_RE = re.compile("|".join(_DB_ERROR_SIGNATURES), re.IGNORECASE)


def verify_error_based(baseline: ProbeResult, payload_result: ProbeResult) -> HeuristicVerdict:
    """
    Looks for a DB error signature in the payload response that was NOT
    present in the baseline. Checking against the baseline (not just
    payload_result in isolation) matters: some apps show generic "500
    error" boilerplate on every request, or a stack trace that would
    otherwise look identical for baseline and payload.

    FALSE POSITIVE RISK: a page that happens to mention SQL error terms
    in unrelated static content (a blog post about databases, API docs)
    would false-positive here. Low likelihood but non-zero -- flag this.
    FALSE NEGATIVE RISK: any app with custom/generic error pages, or
    that suppresses errors entirely (increasingly the norm), produces no
    signal here regardless of whether the injection actually worked.
    """
    baseline_match = _DB_ERROR_RE.search(baseline.body)
    payload_match = _DB_ERROR_RE.search(payload_result.body)

    if payload_match and not baseline_match:
        return HeuristicVerdict(
            signal_detected=True,
            reason=f"DB error signature found in payload response, absent from baseline: "
                   f"'{payload_match.group(0)}'",
            preliminary_risk_rating="HIGH",
        )
    return HeuristicVerdict(signal_detected=False, reason="No new DB error signature detected.", preliminary_risk_rating="INFO")


# ----------------------------------------------------------------------
# SQLi: boolean-based differential
# ----------------------------------------------------------------------
def verify_boolean_differential(
    baseline: ProbeResult, true_result: ProbeResult, false_result: ProbeResult
) -> HeuristicVerdict:
    """
    Compares response SIMILARITY: the TRUE-condition response should
    look like the baseline (or at least significantly MORE like it than
    the FALSE-condition response does), if the injected boolean logic is
    actually reaching the query. Uses difflib's similarity ratio rather
    than raw length -- length alone is fooled by e.g. a single differing
    timestamp shifting length by a few characters.

    FALSE POSITIVE RISK (the most significant one in this whole module):
    any page with per-request-varying content -- CSRF tokens, session
    IDs, "N users online," rotating ads/quotes, A/B test variants -- will
    show a content diff between two ordinary requests even with ZERO
    injection happening. This heuristic cannot distinguish "the query
    logic changed" from "the page is just dynamic." Mitigation attempted
    here: comparing TRUE-vs-FALSE difference magnitude against
    baseline-vs-baseline noise would require a SECOND baseline call,
    which this minimal implementation does not make (cost/rate-limit
    trade-off) -- explicitly flag this as a known gap: a more robust
    version would fetch two baselines and use their diff-ratio as the
    "noise floor" before trusting a TRUE/FALSE differential.
    """
    baseline_vs_true = difflib.SequenceMatcher(None, baseline.body, true_result.body).ratio()
    baseline_vs_false = difflib.SequenceMatcher(None, baseline.body, false_result.body).ratio()

    # TRUE should resemble baseline noticeably more than FALSE does, if
    # the boolean condition is actually influencing query results.
    SIMILARITY_GAP_THRESHOLD = 0.10

    gap = baseline_vs_true - baseline_vs_false
    if gap > SIMILARITY_GAP_THRESHOLD:
        return HeuristicVerdict(
            signal_detected=True,
            reason=(
                f"TRUE-condition response is {gap:.2f} more similar to baseline "
                f"than FALSE-condition response (similarity: baseline~TRUE="
                f"{baseline_vs_true:.2f}, baseline~FALSE={baseline_vs_false:.2f}). "
                f"Suggests the injected boolean logic is influencing query results."
            ),
            preliminary_risk_rating="HIGH",
        )
    return HeuristicVerdict(
        signal_detected=False,
        reason=f"No significant TRUE/FALSE differential (gap={gap:.2f}, threshold={SIMILARITY_GAP_THRESHOLD}).",
        preliminary_risk_rating="INFO",
    )


# ----------------------------------------------------------------------
# Time-based (shared by SQLi and command injection sleep payloads)
# ----------------------------------------------------------------------
def verify_time_delay(
    baseline_samples: list[ProbeResult],
    payload_result: ProbeResult,
    expected_delay_seconds: float = 2.0,
) -> HeuristicVerdict:
    """
    Compares payload response time against baseline MEAN + 3*STDDEV,
    rather than a fixed threshold -- accounts for the target's own
    natural latency variance instead of assuming a flat "normal is <1s."
    Requires >=2 baseline samples to compute stddev meaningfully (see
    pipeline.py, which fetches 2 baseline requests specifically for
    time-based tests).

    FALSE POSITIVE RISK: network jitter, target under unrelated load, or
    a slow downstream dependency (the target app calling a slow external
    API on this exact request) can all produce a delay that has nothing
    to do with our payload. Single-sample time-based tests are
    inherently probabilistic -- this is a fundamental limitation of
    time-based blind detection, not something fixable by better code.
    Mitigation: this implementation requires the observed delay to
    exceed baseline mean+3*stddev AND be within a reasonable window of
    the *expected* delay (not just "much slower than usual," which could
    be anything) -- reduces, does not eliminate, false positives.
    FALSE NEGATIVE RISK: a fast target or heavily cached response could
    mean the injected SLEEP() never actually executes in a code path
    that affects response time (e.g. injected into a query whose result
    is cached from a previous run).
    """
    if len(baseline_samples) < 2:
        return HeuristicVerdict(
            signal_detected=False,
            reason="Insufficient baseline samples for time-based analysis (need >= 2).",
            preliminary_risk_rating="INFO",
        )

    times = [b.elapsed_seconds for b in baseline_samples]
    mean = statistics.mean(times)
    stddev = statistics.stdev(times) if len(times) > 1 else 0.0
    threshold = mean + 3 * stddev

    observed_extra_delay = payload_result.elapsed_seconds - mean
    plausible_window = (expected_delay_seconds * 0.5, expected_delay_seconds * 3.0)

    if (
        payload_result.elapsed_seconds > threshold
        and plausible_window[0] <= observed_extra_delay <= plausible_window[1]
    ):
        return HeuristicVerdict(
            signal_detected=True,
            reason=(
                f"Payload response took {payload_result.elapsed_seconds:.2f}s vs. "
                f"baseline mean {mean:.2f}s (+{stddev:.2f}s stddev), threshold "
                f"{threshold:.2f}s. Extra delay ({observed_extra_delay:.2f}s) falls "
                f"within the expected range for a {expected_delay_seconds}s sleep payload."
            ),
            preliminary_risk_rating="HIGH",
        )
    return HeuristicVerdict(
        signal_detected=False,
        reason=(
            f"Payload response time ({payload_result.elapsed_seconds:.2f}s) did not "
            f"exceed baseline threshold ({threshold:.2f}s) with a plausible delay magnitude."
        ),
        preliminary_risk_rating="INFO",
    )


# ----------------------------------------------------------------------
# XSS: reflected marker (heuristic only -- see module docstring re: this
# NOT being equivalent to confirmed execution)
# ----------------------------------------------------------------------
def verify_reflected_marker(payload: Payload, token: str, rendered_payload: str, payload_result: ProbeResult) -> HeuristicVerdict:
    """
    Checks whether the FULL rendered payload -- syntax characters
    included (< > " ' =), not just the token -- appears unescaped in the
    response.

    IMPORTANT: this checks the whole rendered payload, not just the
    token, deliberately. An earlier version of this function checked
    only the token substring (e.g. "XSS_a1b2c3"), which is pure
    alphanumeric text with no HTML-special characters in it -- meaning
    it would appear identically in the response whether the surrounding
    `<script>` tags were faithfully HTML-encoded (&lt;script&gt;, fully
    inert) or left raw (actually dangerous). Checking token presence
    alone cannot distinguish escaped from unescaped output, which
    defeats the entire purpose of this check. Verified by unit test --
    see the test suite run during development.

    THIS FUNCTION STILL CANNOT CONFIRM ACTUAL JAVASCRIPT EXECUTION even
    with this fix. It confirms "unescaped reflection," which is
    necessary but not sufficient for real XSS impact -- the payload
    could be reflected unescaped but still be inert due to CSP headers,
    being placed in a non-executing context (e.g. inside an HTML
    comment, inside a <textarea>, inside a JSON API response that's
    never rendered as HTML), or browser-side XSS filters. See
    ai_verification.py for the layer that reasons about context, and see
    the optional Playwright-based verify_xss_execution() below for the
    only check in this module that observes REAL execution.

    FALSE POSITIVE RISK: reflected-but-inert placements as described
    above. This is the single biggest reason XSS findings from this
    module should be treated as "possible," not "confirmed," absent the
    Playwright check.
    FALSE NEGATIVE RISK: apps that encode on output but only for some
    characters (e.g. encode < > but not quotes) could still be exploitable
    via a differently-shaped payload not in this minimal set. Also: an app
    that reflects the payload with any whitespace/attribute reordering
    would evade this exact-substring check -- a real implementation might
    use a more tolerant match (e.g. checking each special-character
    fragment independently) at the cost of more false positives.
    """
    token_marker = f"XSS_{token}"
    raw_present = rendered_payload in payload_result.body

    # Distinguish "not present at all" from "present, but HTML-encoded" --
    # decode common entities and check whether the token shows up *only*
    # in that decoded form, which tells us the app encoded it (safe).
    decoded_body = (
        payload_result.body
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&quot;", '"')
        .replace("&#39;", "'")
        .replace("&amp;", "&")
    )
    only_encoded = (not raw_present) and (token_marker in decoded_body)

    if raw_present:
        return HeuristicVerdict(
            signal_detected=True,
            reason=(
                f"Full rendered payload found unescaped in response body "
                f"(matched on syntax, not just the token). NOTE: confirms "
                f"reflection, not confirmed execution -- see AI verification "
                f"/ optional headless-browser check."
            ),
            preliminary_risk_rating="MEDIUM",  # capped at MEDIUM here specifically
            # because this heuristic alone can't confirm execution --
            # AI verification or the Playwright check may raise this.
        )
    if only_encoded:
        return HeuristicVerdict(
            signal_detected=False,
            reason=f"Marker '{token_marker}' found only after decoding HTML entities -- output is being escaped correctly.",
            preliminary_risk_rating="INFO",
        )
    return HeuristicVerdict(signal_detected=False, reason="Payload not found in response (raw or encoded).", preliminary_risk_rating="INFO")


async def verify_xss_execution_playwright(url: str, token: str) -> HeuristicVerdict | None:
    """
    OPTIONAL, stronger verification: actually renders the page in a
    headless browser and checks whether document.title was really
    changed by executed JavaScript -- the only check in this module that
    observes true execution rather than inferring it from response text.

    Returns None (not a false HeuristicVerdict) if Playwright isn't
    installed, so callers can distinguish "we checked and found nothing"
    from "we couldn't check." Requires: pip install playwright &&
    playwright install chromium -- not in requirements.txt by default
    since it's a heavier dependency (downloads a browser binary) that
    not every deployment will want.
    """
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        return None

    expected_title = f"XSS_{token}"

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        try:
            page = await browser.new_page()
            await page.goto(url, timeout=10_000, wait_until="networkidle")
            title = await page.title()
        finally:
            await browser.close()

    if title == expected_title:
        return HeuristicVerdict(
            signal_detected=True,
            reason=f"Headless browser confirmed JS execution: document.title was set to '{expected_title}'.",
            preliminary_risk_rating="CRITICAL",  # confirmed execution, not just reflection
        )
    return HeuristicVerdict(
        signal_detected=False,
        reason="Headless browser did not observe the expected title change -- payload did not execute.",
        preliminary_risk_rating="INFO",
    )


# ----------------------------------------------------------------------
# Command injection: executed marker
# ----------------------------------------------------------------------
def verify_executed_marker(token: str, baseline: ProbeResult, payload_result: ProbeResult) -> HeuristicVerdict:
    """
    Looks for the command's echoed output marker in the response, absent
    from baseline. Because the token is a random per-run UUID fragment,
    a match essentially rules out coincidence.

    FALSE POSITIVE RISK: extremely low given the random token, UNLESS
    the app reflects raw user input back verbatim in the response body
    without executing anything (e.g. a search page that echoes "you
    searched for: <input>") -- in that case the marker "VULN_{token}"
    would appear simply because we sent the string "; echo VULN_{token}"
    and the app printed our whole input back unexecuted. This is the
    main failure mode for this check and is exactly the kind of judgment
    call handed to AI verification: "does the surrounding text look like
    executed command output, or like our literal input being echoed back?"
    FALSE NEGATIVE RISK: command output frequently isn't reflected in the
    HTTP response at all (goes to a log file, a background job, etc.) --
    the time-based payload exists specifically to catch that case, but
    even that only detects impact when the injected command measurably
    affects timing.
    """
    marker = f"VULN_{token}"
    if marker in payload_result.body and marker not in baseline.body:
        return HeuristicVerdict(
            signal_detected=True,
            reason=f"Command output marker '{marker}' found in response, absent from baseline.",
            preliminary_risk_rating="HIGH",
        )
    return HeuristicVerdict(signal_detected=False, reason="No command output marker detected.", preliminary_risk_rating="INFO")
