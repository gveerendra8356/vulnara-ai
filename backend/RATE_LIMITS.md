# Gemini Free Tier: Rate Limits & Failure Handling

## What the limits actually are

Google's free tier for Gemini models (the `gemini-1.5-flash` / equivalent
flash-tier models this project targets) is expressed as three separate caps:
**RPM** (requests per minute), **TPM** (tokens per minute), and **RPD**
(requests per day). The exact numbers have changed more than once as Google
adjusts free-tier offerings, so **do not hardcode a number from this doc
into your report as gospel** — check https://ai.google.dev/pricing (or
https://ai.google.dev/gemini-api/docs/rate-limits) right before you write
that section, and note the numbers you found + the date you checked them.
As of this project's design, treat free-tier RPM as low (roughly
single-to-low-double-digits per minute) — the practical implication is
the same regardless of the exact figure: **you cannot fire one Gemini call
per open port on a scan** without hitting the ceiling on anything but the
smallest target.

## Why the design already accounts for this

1. **Batching per host, not per port** (`prompts.py` / `pipeline.py`) — a
   host with 15 open ports is one Gemini call, not 15. This is the single
   biggest lever for staying under RPM on any realistically sized scan.
2. **NVD candidate trimming** — only the fields Gemini actually needs go
   into the prompt (not full raw NVD JSON), which helps against the TPM
   cap as much as RPM.
3. **Low temperature (0.2)** — doesn't affect rate limits directly, but
   reduces the odds of a malformed response that would otherwise burn a
   second call via the corrective-reprompt path.

## Failure handling implemented in `gemini_client.py`

| Failure mode | How it's handled |
|---|---|
| `429 ResourceExhausted` (rate limit hit) | Exponential backoff with jitter, 3 inner retries, inside `_call_with_backoff`. |
| `503 ServiceUnavailable` (transient outage) | Same backoff path as above — Gemini treats these similarly in practice. |
| Malformed/invalid JSON despite `response_schema` | One corrective re-prompt: the invalid output + the Pydantic validation error is sent back to Gemini with an explicit "fix this" instruction, rather than immediately failing. |
| Repeated failure after all retries | Raises `GeminiTriageError`. In the triage pipeline, this is caught **per host** — one host's AI failure doesn't abort the whole scan; the rest of the hosts still get triaged and written. In the remediation path, it surfaces as an HTTP `502` to the caller (distinguishable from a real app bug). |

## What isn't handled yet, and should be before a real client demo

- **Daily quota (RPD) exhaustion mid-demo.** Backoff helps with per-minute
  bursts, not with "you've used your whole day's free quota." Your
  architecture already names the mitigation for this: **Ollama as a
  self-hosted fallback**. The clean way to wire that in is a single
  feature-flag / try-Gemini-then-fall-back-to-Ollama wrapper one layer
  above `gemini_client.py`'s public functions (`run_triage_call`,
  `run_remediation_call`) — catch `GeminiTriageError` specifically when
  its root cause was quota exhaustion (not a validation failure) and
  retry the same prompt against a local Ollama model using the same
  Pydantic schemas for validation. This project's code doesn't implement
  that fallback yet — it's a natural "future work" item for your report,
  and a good one to actually build if you have time, since it's exactly
  the kind of resilience story a client handover values.
- **A circuit breaker.** Right now, if Gemini is down for an extended
  period, every scan will independently retry-and-fail through the full
  backoff sequence, which is slow for the user and wastes retry budget.
  A simple shared circuit-breaker flag (open after N consecutive failures
  across any call, half-open retry after a cooldown) would fail fast
  instead. Not implemented here to keep this module's scope to what was
  asked, but worth a paragraph in your "future improvements" section.
- **Cost/quota monitoring.** Even on free tier, it's worth logging token
  usage per call (Gemini's response includes usage metadata) so you have
  real numbers for your report on how many scans/day the free tier
  actually supports at your batching granularity.
