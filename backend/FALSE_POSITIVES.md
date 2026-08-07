# Active Testing Module — Known False Positive / False Negative Sources

Collected from inline comments across `active_testing/`, for your
thesis limitations section. Organized by cause, since several apply
across multiple attack types.

## 1. Dynamic page content (affects: SQLi boolean-differential)

`verify_boolean_differential()` compares response similarity between a
TRUE-condition and FALSE-condition payload. Any page with per-request
varying content — CSRF tokens, session IDs, "N users online" counters,
rotating ads, timestamps — will show a content diff between two
*ordinary* requests, with zero injection involved. This is the single
largest false-positive risk in the module.

**Mitigation implemented**: comparison is similarity-ratio-based
(difflib), not raw length, and requires the TRUE response to be
*meaningfully* more similar to baseline than the FALSE response is
(threshold, not just "any difference").

**Mitigation NOT implemented** (flag as future work): fetching a second
baseline and using baseline-vs-baseline noise as a floor before trusting
any TRUE/FALSE differential. Left out here specifically to keep request
volume down under the rate-limiting/budget constraints — a real
production version would likely accept the extra requests for the
accuracy gain.

## 2. Network jitter and target load (affects: all time-based detection)

`verify_time_delay()` is used for both SQLi (`SLEEP()`) and command
injection time-based probes. Any latency variance unrelated to the
payload — network jitter, the target under unrelated load, a slow
downstream dependency the target app happens to call on this specific
request — can produce a delay indistinguishable from a real injection
effect.

**Mitigation implemented**: threshold is baseline mean + 3×stddev
(computed from 2 baseline samples), not a fixed number, and the observed
extra delay must fall within a plausible window of the *expected* sleep
duration, not just "much slower than usual."

**Residual risk**: this is a fundamental limitation of time-based blind
detection generally, not something fully fixable in code. Any
time-based finding from this module should be treated as lower-confidence
than error-based or marker-based findings by design.

## 3. Reflection ≠ execution (affects: XSS)

`verify_reflected_marker()` can only confirm that the payload string
appears *unescaped* in the response body — it cannot confirm the
JavaScript actually ran. A payload can be reflected unescaped and still
be completely inert if it lands in a non-executing context: inside an
HTML comment, inside a `<textarea>`, inside a JSON API response that's
never rendered as HTML, or blocked at render time by a Content-Security-
Policy header this module doesn't inspect.

**A bug worth citing directly**: during development, unit testing this
function against a synthetic fully-HTML-encoded response (`&lt;script&gt;
document.title=&#39;XSS_token&#39;&lt;/script&gt;`) revealed that an
earlier version checked only the random *token* substring for presence —
and the token itself (plain alphanumeric text) is untouched by HTML entity
encoding, so it appeared identically whether the surrounding markup was
safely encoded or not. That version would have reported every properly-
encoded, non-vulnerable response as a positive XSS finding. Fixed by
checking the *full rendered payload*, syntax characters included, so
encoding of `< > " '` is actually detected. This is worth including in
your report as a concrete example of why naive substring/pattern
matching is an unreliable verification strategy — exactly the failure
mode your project spec's "not just pattern match" requirement is
guarding against — and why it was caught by testing against a realistic
encoded-response case rather than only a raw-reflection case.

**Mitigation implemented (after the fix)**: two layers.
1. AI verification (`ai_verification.py`) is explicitly prompted to reason
   about placement context, not just presence.
2. An optional headless-browser check (`verify_xss_execution_playwright`)
   observes *real* execution via `document.title`, when Playwright is
   installed. This is the only check in the module that confirms true
   execution rather than inferring it.

**Residual risk**: without the Playwright check enabled, all XSS findings
from this module are "possible reflection," not "confirmed execution" —
say so explicitly in your report rather than presenting them as verified.

## 4. Literal input echo vs. real command output (affects: command injection)

`verify_executed_marker()`'s biggest failure mode: an app that echoes raw
user input back verbatim (e.g. "you searched for: `<input>`") without
executing anything will still show the marker string in its response,
because we *sent* the string `"; echo VULN_{token}"` — the marker was
never executed, just echoed back as literal text.

**Mitigation implemented**: the random per-run token rules out
coincidental matches against unrelated content, but does NOT distinguish
"executed and printed" from "echoed verbatim." This distinction is
explicitly handed to AI verification, which is prompted to reason about
whether the surrounding text looks like genuine command output.

## 5. DB-engine-specific payloads (affects: SQLi time-based)

The time-based SQLi payload (`SLEEP(2)`) is MySQL-specific. Postgres uses
`pg_sleep()`, MSSQL uses `WAITFOR DELAY`, Oracle uses `DBMS_LOCK.SLEEP`.
This module does not fingerprint the backend database first, so it will
systematically **under-detect** (false negative) time-based SQLi against
any non-MySQL backend. A production tool would run a lightweight DB
fingerprint step first and select the matching payload dialect.

## 6. Error signature coverage (affects: SQLi error-based)

`_DB_ERROR_SIGNATURES` is a small, illustrative list, not exhaustive.
Custom error pages, localized error messages, or DB versions with
different wording will produce no signal — a false negative, not a false
positive, but worth noting: absence of an error-based signal is very
weak evidence of absence of SQLi.

Conversely (lower-probability false positive): a page whose *legitimate*
content happens to mention SQL error terminology (a blog post about
databases, API documentation) could match the regex. Low likelihood, but
non-zero.

## 7. AI verification is itself probabilistic

The entire verification pipeline's final layer is a Gemini call
reasoning over heuristic evidence and a response snippet. This is a
significant accuracy improvement over pure string-matching, but it is
not ground truth — it can misjudge ambiguous cases in either direction,
and its judgment quality is bounded by how much context fits in the
truncated response snippet it's given (3000 chars around the relevant
evidence, not the full page).

## 8. Discovery scope (affects: what gets tested at all, not verification accuracy)

`discovery.py` is single-page, static-HTML-only, unauthenticated. Forms
rendered client-side by a JS framework, forms behind a login, or forms
on any page other than the root URL of each discovered HTTP(S) port will
simply never be tested — not a false positive, but a coverage gap worth
stating plainly: **a clean active-testing result from this module means
"no issues found in what was discovered and tested," not "no issues
exist."**

## Overarching design point for your limitations section

Every finding this module produces is written to `Threat_Logs` with an
explicit `ai_verified` boolean and `risk_rating` — never silently
promoted to a confirmed `Vulnerabilities` entry or fed automatically into
remediation. Given the false-positive/negative sources above, that
human-review boundary (already a non-negotiable design principle across
the whole project) is doing real, necessary work here, not just
satisfying a policy checkbox.
