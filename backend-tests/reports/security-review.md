# Security Review -- Vulnara Backend

This generated report summarizes the current curated findings and their
regression-test references. It is not a new independent security review.
See `findings.xlsx` for the machine-readable finding list.

## What was tested well and holds up
- **SQL injection:** every free-text field (scan target, justification,
  login credentials) was fuzzed with 15 classic SQLi payloads; the
  SQLAlchemy async ORM's parameterized queries held in every case.
- **Command / argument injection:** `nmap` is invoked via
  `asyncio.create_subprocess_exec` with an argument list (never `shell=True`);
  target validation remains a separate concern.
- **Path traversal:** no field is ever used as a filesystem path; traversal
  payloads are stored/rejected as inert text.
- **JWT security:** `alg: none`, algorithm-confusion, weak-secret guessing,
  payload tampering, truncation, and trailing-garbage tokens were all
  correctly rejected.
- **Session teardown:** logout genuinely denylists the refresh token --
  confirmed across repeated post-logout refresh attempts, not just once.
- **Primary scan ownership:** `/scans/*` correctly scopes access by owner,
  with an admin override, verified via a real two-client-account IDOR setup
  (not just "authenticated vs not").

## Curated follow-up items

### VULN-004 -- Injection / Argument Injection (Medium)
**Endpoint(s):** `POST /scans`

The API accepts targets beginning with '-'. The scanner passes the target as a subprocess argument, not through a shell; however, nmap option parsing for such a target has not been exercised end to end.

**Impact:** A leading dash could be interpreted as a scanner option if target parsing does not terminate options.

**Evidence:** `test_injection.py::TestCommandInjection::test_target_starting_with_dash_does_not_crash_api`

**Recommended fix:** Reject targets starting with '-' or use the scanner's supported option terminator before the target.

### VULN-005 -- SSRF (High)
**Endpoint(s):** `POST /scans`

The API permits internal, loopback, and link-local targets after the user confirms authorization. This is expected for authorized internal assessments, but deployments serving untrusted tenants may need an explicit target-range policy.

**Impact:** Without tenant isolation or target policy, a user could cause the service to probe networks reachable from the backend.

**Evidence:** `test_injection.py::TestSsrfStyleTargets (6 parametrized targets, all currently accepted)`

**Recommended fix:** Define a deployment-specific allow-list or authorization policy for reachable target ranges; do not blanket-block private networks when internal scanning is intended.

### VULN-008 -- Configuration / Security Headers (Low)
**Endpoint(s):** `All endpoints`

No security response headers are set at the application layer: X-Content-Type-Options, X-Frame-Options, Strict-Transport-Security, Content-Security-Policy are all absent, and the default 'Server: uvicorn' banner is exposed.

**Impact:** Minor defense-in-depth gap; low real-world impact for a pure JSON API but worth closing, especially if any HTML/Swagger UI is ever exposed.

**Evidence:** `test_configuration.py::TestMissingSecurityHeaders (5 tests)`

**Recommended fix:** Add a small ASGI middleware (or reverse-proxy config) to set the standard security headers on every response; consider suppressing the Server header.

### VULN-009 -- Configuration / Rate Limiting (High)
**Endpoint(s):** `POST /auth/login, POST /auth/register`

No HTTP-layer rate limiting exists anywhere in the application; a burst of 15 failed logins against one account, and 10 rapid registrations, all completed with no 429 response.

**Impact:** No built-in protection against credential-stuffing/brute-force login attempts or registration spam.

**Evidence:** `test_configuration.py::TestRateLimiting (2 tests)`

**Recommended fix:** Add per-IP and per-account rate limiting on /auth/login and /auth/register (e.g. via slowapi or a reverse-proxy rule).

## Methodology notes
- The HTTP integration tests run against a real `uvicorn` process bound to
  an ephemeral SQLite database, not against route handlers called directly
  in-process -- so CORS middleware, JSON parsing, and the real JWT auth
  dependency are all genuinely exercised on every request.
- `nmap` is not available in this environment, so background scan execution
  itself was not (and cannot be) exercised end-to-end here; all scan-related
  tests assert against the synchronous API contract only.
- No live AI (Groq/Gemini) credentials are configured, so remediation
  generation was tested up to the point of the outbound AI call.
