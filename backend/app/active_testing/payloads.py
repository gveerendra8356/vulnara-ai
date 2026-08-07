"""
active_testing/payloads.py

A deliberately MINIMAL, canonical payload set -- three attack types,
2-3 payloads each. This is not, and is not meant to be, an exhaustive
attack library (no WAF-bypass encodings, no polyglots, no blind
exfiltration chains, no multi-stage payloads). Each payload here exists
to answer one narrow question: "does this input reach an unsafe sink
without being neutralized?" -- which is the appropriate scope for a
defensive/educational scanning tool whose job is to flag a risk for
human review, not to actually exploit anything.

Every payload includes a unique, randomly generated TOKEN placeholder
substituted in at test-time (see pipeline.py). This is the single most
important anti-false-positive design choice in this module: a random
per-run token means "the token appears in the response" can only be
explained by the payload actually reaching and affecting the response --
it rules out coincidental string matches against static page content.

DB ENGINE CAVEAT (flag for your limitations section):
The SQLi payloads below are MySQL-flavored (SLEEP()). Postgres uses
pg_sleep(), MSSQL uses WAITFOR DELAY, Oracle uses DBMS_LOCK.SLEEP. A
production-grade tool would fingerprint the backend DB first and select
the matching payload dialect. This starter set does not do that -- it
will under-detect time-based SQLi against non-MySQL backends. Documented
in FALSE_POSITIVES.md as a known false-negative source.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class AttackType(str, Enum):
    SQLI = "SQLI"
    XSS = "XSS"
    CMDI = "CMDI"  # NOTE: requires the schema migration in
                   # migrations/002_add_cmdi_attack_type.sql -- the
                   # original Task 1 CHECK constraint only allowed
                   # ('SQLI','XSS'). Flagging this explicitly rather
                   # than silently writing a value the DB will reject.


class DetectionStrategy(str, Enum):
    """
    How verifiers.py should interpret the result of sending this payload.
    Different payload types need fundamentally different verification
    logic (see verifiers.py) -- this tag routes each payload to the
    right check.
    """
    ERROR_SIGNATURE = "error_signature"   # look for DB/shell error text
    BOOLEAN_DIFFERENTIAL = "boolean_differential"  # compare TRUE vs FALSE response
    TIME_DELAY = "time_delay"             # measure response latency
    REFLECTED_MARKER = "reflected_marker" # look for unescaped token in body
    EXECUTED_MARKER = "executed_marker"   # requires real execution (headless browser / real command output)


@dataclass(frozen=True)
class Payload:
    attack_type: AttackType
    name: str
    template: str  # "{token}" gets substituted at test time
    detection_strategy: DetectionStrategy
    description: str
    # Paired "control" payload for differential tests (boolean-based SQLi
    # needs a TRUE and a FALSE variant to compare against each other AND
    # against a no-payload baseline -- see verifiers.py).
    control_template: str | None = None


# ----------------------------------------------------------------------
# SQL Injection -- 3 payloads covering the three classic detection
# techniques (error-based, boolean-based, time-based). Each represents a
# different way SQLi can manifest depending on how the app handles DB
# errors (some suppress them entirely, which is exactly why we need more
# than just the error-based check).
# ----------------------------------------------------------------------
SQLI_PAYLOADS: list[Payload] = [
    Payload(
        attack_type=AttackType.SQLI,
        name="error_based_single_quote",
        template="'",
        detection_strategy=DetectionStrategy.ERROR_SIGNATURE,
        description=(
            "A lone single quote breaks naive string-concatenated SQL "
            "queries, often surfacing a raw DB error in the response if "
            "errors aren't suppressed."
        ),
    ),
    Payload(
        attack_type=AttackType.SQLI,
        name="boolean_based_or_true",
        template="' OR '1'='1' -- ",
        control_template="' OR '1'='2' -- ",
        detection_strategy=DetectionStrategy.BOOLEAN_DIFFERENTIAL,
        description=(
            "Compares the response to an always-TRUE condition against an "
            "always-FALSE condition (control_template). A real SQLi "
            "vulnerability typically returns visibly different content "
            "(e.g. more rows, a login bypass) for TRUE vs FALSE, even when "
            "errors are fully suppressed."
        ),
    ),
    Payload(
        attack_type=AttackType.SQLI,
        name="time_based_sleep_mysql",
        template="' OR SLEEP(2)-- -",
        detection_strategy=DetectionStrategy.TIME_DELAY,
        description=(
            "MySQL-specific time-based blind SQLi probe. A 2-second delay "
            "is intentionally short (minimizes load on the target) while "
            "still being well outside normal network jitter when measured "
            "against a baseline (see verifiers.py). MySQL-only -- see "
            "module docstring for the DB-engine caveat."
        ),
    ),
]

# ----------------------------------------------------------------------
# XSS -- 3 payloads covering three common reflection contexts: raw HTML
# body, breaking out of an HTML attribute, and an SVG-tag variant that
# survives some naive `<script>`-string-blocklist filters (still a very
# basic bypass, included because "does the app just blocklist the
# literal string <script>" is a genuinely common, worth-testing-for weakness).
# Each uses document.title as the execution signal because it's easy to
# check both via simple string presence AND, if using the optional
# headless-browser verifier, via a real DOM read.
# ----------------------------------------------------------------------
XSS_PAYLOADS: list[Payload] = [
    Payload(
        attack_type=AttackType.XSS,
        name="basic_script_tag",
        template="<script>document.title='XSS_{token}'</script>",
        detection_strategy=DetectionStrategy.REFLECTED_MARKER,
        description="Classic reflected XSS probe in an HTML body context.",
    ),
    Payload(
        attack_type=AttackType.XSS,
        name="attribute_breakout",
        template="\"><img src=x onerror=\"document.title='XSS_{token}'\">",
        detection_strategy=DetectionStrategy.REFLECTED_MARKER,
        description=(
            "Tests whether user input placed inside an HTML attribute "
            "(e.g. value=\"...\") can break out of the attribute and inject "
            "a new element -- a very common real-world XSS pattern, "
            "distinct from the basic body-context case above."
        ),
    ),
    Payload(
        attack_type=AttackType.XSS,
        name="svg_onload_bypass",
        template="<svg onload=\"document.title='XSS_{token}'\">",
        detection_strategy=DetectionStrategy.REFLECTED_MARKER,
        description=(
            "Doesn't contain the literal substring '<script', so it "
            "surfaces apps that naively blocklist that one string instead "
            "of properly encoding output."
        ),
    ),
]

# ----------------------------------------------------------------------
# Command Injection -- 3 payloads covering the common shell metacharacter
# injection points (;, |, &&) plus a time-based variant for cases where
# command output isn't reflected back to the response at all.
# ----------------------------------------------------------------------
CMDI_PAYLOADS: list[Payload] = [
    Payload(
        attack_type=AttackType.CMDI,
        name="semicolon_echo",
        template="; echo VULN_{token}",
        detection_strategy=DetectionStrategy.EXECUTED_MARKER,
        description="Command chaining via semicolon; looks for echoed marker in response.",
    ),
    Payload(
        attack_type=AttackType.CMDI,
        name="pipe_echo",
        template="| echo VULN_{token}",
        detection_strategy=DetectionStrategy.EXECUTED_MARKER,
        description="Command chaining via pipe -- catches inputs used directly as a pipeline argument.",
    ),
    Payload(
        attack_type=AttackType.CMDI,
        name="time_based_sleep",
        template="; sleep 2",
        detection_strategy=DetectionStrategy.TIME_DELAY,
        description=(
            "For cases where command output isn't reflected in the "
            "response at all (very common for command injection -- output "
            "often just goes to a log or is discarded). A measurable "
            "delay is possible even with zero output reflection."
        ),
    ),
]

ALL_PAYLOADS: dict[AttackType, list[Payload]] = {
    AttackType.SQLI: SQLI_PAYLOADS,
    AttackType.XSS: XSS_PAYLOADS,
    AttackType.CMDI: CMDI_PAYLOADS,
}


def render(payload: Payload, token: str, control: bool = False) -> str:
    """Substitutes the per-run random token into a payload template."""
    template = payload.control_template if (control and payload.control_template) else payload.template
    return template.format(token=token)
