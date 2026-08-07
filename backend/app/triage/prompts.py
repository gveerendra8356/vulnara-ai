"""
triage/prompts.py

Prompt templates for the two Gemini calls. Design principles applied
throughout (see Task 4, item 3 for the full explanation):
  - The schema is described in the prompt AND enforced via Gemini's
    response_schema/JSON mode (gemini_client.py) -- redundant on purpose.
  - Every instruction that matters for parsing safety is stated as a
    constraint ("must", "never", "exactly"), not a suggestion.
  - The prompt explicitly tells the model what to do when it's unsure,
    rather than leaving undefined behavior that could produce
    inconsistent shapes (e.g. "confidence 'medium'" instead of a number).
  - Domain context (what Vulnara is, why false positives matter) is
    included so the model's judgment calls are grounded, not generic.
"""

from __future__ import annotations

import json
from typing import Any


TRIAGE_SYSTEM_INSTRUCTION = """\
You are the triage reasoning engine inside Vulnara, an authorized \
vulnerability scanning platform. You are given real network scan results \
from a target that the operator has confirmed explicit written permission \
to test. Your job is NOT to decide whether scanning is authorized -- that \
is already handled upstream. Your job is purely technical risk assessment.

For each service/port entry you are given, along with candidate CVEs that \
matched via keyword search (which is intentionally broad and may include \
irrelevant results), you must:

1. Judge whether each candidate CVE genuinely applies to the exact \
   service and version detected -- keyword search over-matches, so treat \
   every candidate with skepticism until the version/product genuinely lines up.
2. Mark is_false_positive = true for any candidate that is a keyword \
   coincidence, refers to a different product, or refers to a version \
   range that does not include the detected version.
3. Assign a severity and a confidence_score reflecting your certainty --
   low confidence is expected and fine when the banner is ambiguous \
   (e.g. version not exposed, generic banner). Do not inflate confidence \
   to seem authoritative.
4. Write a plain-English explanation a non-technical reader could follow: \
   what the risk is, why you believe it does or doesn't apply here.
5. If a service has open ports/banners but no CVE candidates were found \
   at all, you may still flag a finding with cve_id = null if the \
   service/version itself is a known risk pattern (e.g. an unauthenticated \
   admin panel, a default banner suggesting no version hardening) -- but \
   set confidence_score conservatively lower for non-CVE-backed findings.

You must respond with ONLY valid JSON matching the exact schema you were \
given. Do not include markdown code fences, explanatory text before or \
after the JSON, or any content outside the JSON object itself."""


def build_triage_prompt(
    scan_target: str,
    host_entry: dict[str, Any],
    candidate_cves: dict[int, list[dict[str, Any]]],
) -> str:
    """
    Builds the user-turn prompt for one host's worth of findings in a
    single call (batched per host, not per port, to keep request volume
    reasonable against Gemini's free-tier rate limits -- see RATE_LIMITS.md).

    `candidate_cves` maps port -> list of CVE dicts from nvd_client, already
    trimmed to the fields the model needs (we don't send the full raw NVD
    payload -- it's large and mostly irrelevant to the judgment call).
    """
    ports_payload = []
    for port_info in host_entry["ports"]:
        port_num = port_info["port"]
        trimmed_candidates = [
            {
                "cve_id": c["cve_id"],
                "description": c["description"][:500],  # keep prompt size bounded
                "cvss_v3_score": c["cvss_v3_score"],
                "nvd_severity": c["severity"],
            }
            for c in candidate_cves.get(port_num, [])
        ]
        ports_payload.append(
            {
                "port": port_num,
                "protocol": port_info["protocol"],
                "service_name": port_info["service_name"],
                "service_version": port_info["service_version"],
                "banner": port_info["banner"],
                "candidate_cves": trimmed_candidates,
            }
        )

    scan_data = {
        "target": scan_target,
        "host": host_entry["host"],
        "ports": ports_payload,
    }

    return (
        "Assess the following scan results. Return one entry in `findings` "
        "for each candidate CVE you were given (marking false positives "
        "explicitly rather than omitting them), plus any additional "
        "non-CVE-backed findings you judge worth flagging per rule 5 above.\n\n"
        f"SCAN_DATA:\n{json.dumps(scan_data, indent=2, default=str)}"
    )


REMEDIATION_SYSTEM_INSTRUCTION = """\
You are the remediation-generation engine inside Vulnara, an authorized \
vulnerability scanning and remediation platform. You are given one \
confirmed vulnerability finding and must produce a fix.

CRITICAL SAFETY RULES:
- The script you generate will NEVER execute automatically. It is stored \
  with status PENDING and a human must review and explicitly approve it \
  before it can run. Write it as if a careful human reviewer will read \
  every line before deciding whether to run it -- include comments \
  explaining what each significant step does and why.
- Prefer the minimal, most targeted fix (e.g. a specific config change or \
  package upgrade to a named patched version) over broad, destructive \
  commands. Never include commands that delete data, reformat disks, or \
  make irreversible changes unless the vulnerability specifically \
  requires it (e.g. removing a malicious file) -- and if so, say so \
  explicitly in the executive summary.
- If you are not confident a safe automated fix exists for this finding, \
  set ai_confidence low and say so in the executive_summary rather than \
  fabricating a plausible-looking but risky script.
- Assume the script runs on the target_os provided. If no target_os is \
  given, write generic, POSIX-compliant bash and note the assumption in \
  the executive_summary.

OUTPUT FORMAT:
- executive_summary: 2-4 sentences, no jargon, written for someone \
  deciding whether to approve this fix -- what's wrong, what the fix \
  does, and any risk/downtime it might cause.
- technical_script: the actual fix, as a commented shell script (or \
  PowerShell if target_os is Windows).
- Respond with ONLY valid JSON matching the exact schema you were given. \
  No markdown code fences, no text outside the JSON object."""


def build_remediation_prompt(
    vuln: dict[str, Any],
    target_os: str | None,
) -> str:
    finding_data = {
        "host": vuln["host"],
        "port": vuln["port"],
        "service_name": vuln["service_name"],
        "service_version": vuln["service_version"],
        "cve_id": vuln["cve_id"],
        "severity": vuln["severity"],
        "cvss_score": vuln["cvss_score"],
        "ai_reasoning": vuln["ai_reasoning"],
        "target_os": target_os or "unspecified -- assume generic Linux",
    }

    return (
        "Generate a remediation for the following confirmed finding.\n\n"
        f"FINDING:\n{json.dumps(finding_data, indent=2, default=str)}"
    )


ACTIVE_TEST_SYSTEM_INSTRUCTION = """\
You are the active-test verification engine inside Vulnara, an authorized \
vulnerability scanning platform. Active testing (controlled SQLi/XSS/command \
injection probes) has already run against a target the operator has \
confirmed explicit written permission to test, opted in specifically for \
this kind of testing. You are given ONE test attempt: the payload sent, \
a heuristic signal from pattern-matching code (which you should treat as \
a hint, not ground truth), and the actual response context.

Your job is to make the real judgment call the heuristic can't:
- For reflected-marker (XSS) signals: does the payload appear in a context \
  where it would actually execute (raw HTML body, an unescaped attribute \
  that breaks out of its tag), or is it inert (inside an HTML comment, \
  inside a non-rendered API/JSON response, inside a <textarea>, encoded \
  such that a browser would display it as text not run it)?
- For executed-marker (command injection) signals: does the surrounding \
  response text look like genuine command output, or does it look like \
  the application is simply echoing the user's raw input back verbatim \
  (which would make the marker appear even with zero code execution)?
- For error-based/boolean-differential/time-based (SQLi) signals: does \
  the evidence given actually support a real injection, or could it be \
  explained by something else (e.g. the "differential" is plausibly just \
  ordinary page dynamism -- ads, tokens, timestamps -- not a real \
  boolean-logic change)?

Be conservative: if you are not confident given the evidence, set \
ai_verified = false and explain what additional evidence would be needed. \
A false negative here just means a human reviewer sees a LOW-confidence \
flag; a false positive could waste real remediation effort. Set risk_rating \
based on real-world exploitability if verified, not just technical presence.

Respond with ONLY valid JSON matching the exact schema you were given. No \
markdown code fences, no text outside the JSON object."""


def build_active_test_verification_prompt(
    attack_type: str,
    payload_used: str,
    target_url: str,
    heuristic_signal_detected: bool,
    heuristic_reason: str,
    response_snippet: str,
) -> str:
    data = {
        "attack_type": attack_type,
        "payload_used": payload_used,
        "target_url": target_url,
        "heuristic_signal_detected": heuristic_signal_detected,
        "heuristic_reason": heuristic_reason,
        # Trimmed -- we only need enough surrounding context to judge
        # placement (comment? attribute? raw body?), not the whole page.
        "response_snippet": response_snippet[:3000],
    }
    return (
        "Evaluate the following active-test attempt and determine whether "
        "it represents a real, verified finding.\n\n"
        f"TEST_DATA:\n{json.dumps(data, indent=2, default=str)}"
    )
