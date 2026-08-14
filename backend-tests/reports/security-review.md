# Security Review -- Vulnara Backend

This review is based on (1) a manual read of every route, schema, and model
in `backend/app/`, and (2) 10 findings confirmed by automated
tests that exercise the real, running application over HTTP -- not just a
static-analysis pass. See `test-cases.xlsx` for the full 400-case suite and
`findings.xlsx` for the machine-readable finding list.

## What was tested well and holds up
- **SQL injection:** every free-text field (scan target, justification,
  login credentials) was fuzzed with 15 classic SQLi payloads; the
  SQLAlchemy async ORM's parameterized queries held in every case.
- **Command / argument injection:** `nmap` is invoked via
  `asyncio.create_subprocess_exec` with an argument list (never `shell=True`),
  confirmed safe against shell metacharacter payloads -- though see VULN-004
  for a narrower argument-injection edge case.
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

## Confirmed findings

### VULN-001 -- Authorization / IDOR (Critical)
**Endpoint(s):** `GET /vulnerabilities/{vuln_id}, GET /remediations/{rem_id}, GET /remediations`

Neither GET /vulnerabilities/{id} nor GET /remediations/{id} performs any ownership/tenant check, unlike the equivalent /scans/* endpoints. Any authenticated user of any role can read any other tenant's vulnerability or remediation data by ID or via the unscoped list endpoint.

**Impact:** Cross-tenant data disclosure of vulnerability and remediation details, including AI-generated remediation scripts.

**Evidence:** `test_authorization.py::TestKnownIdorGaps (3 tests, all confirming current 200 OK behavior)`

**Recommended fix:** Add the same scan-ownership join check used in scans.py (scan.user_id == current_user.user_id or role == 'admin') to get_vulnerability, get_remediation, and list_remediations.

### VULN-002 -- Authentication / Availability (Critical)
**Endpoint(s):** `POST /auth/register`

Registering with a password longer than bcrypt's 72-byte input cap raises an unhandled exception, returning an HTTP 500 instead of a clean validation error.

**Impact:** Unauthenticated crash-inducing input on a public endpoint; potential denial-of-service / log-noise vector.

**Evidence:** `test_authentication.py::TestRegistration::test_register_extremely_long_password_does_not_crash (reproducibly fails)`

**Recommended fix:** Add an explicit max_length (e.g. 72) to UserRegisterRequest.password, or truncate/reject before passing to passlib.

### VULN-003 -- Input Validation (Low)
**Endpoint(s):** `PATCH /vulnerabilities/{vuln_id}`

VulnerabilityUpdateRequest.status is a bare `str` with no Literal/enum constraint and no DB-level CHECK constraint; any string, including empty or garbage values, is persisted as-is.

**Impact:** Data-integrity risk -- downstream code filtering/branching on status values may silently mishandle unexpected values.

**Evidence:** `test_input_validation.py::TestVulnerabilityUpdateValidation (5 tests, confirming current 200 OK behavior)`

**Recommended fix:** Constrain status to Literal['OPEN','CONFIRMED','FALSE_POSITIVE','REMEDIATED'] (or equivalent) in the schema.

### VULN-004 -- Injection / Argument Injection (Medium)
**Endpoint(s):** `POST /scans`

The `target` field applies no allow-list or leading-character restriction; a target beginning with '-' could be interpreted as an nmap flag by argument position once it reaches the scanner, even though the subprocess call itself is not shell-based.

**Impact:** Potential argument-injection into the nmap invocation (e.g. forcing output-file flags or altering scan behavior).

**Evidence:** `test_injection.py::TestCommandInjection::test_target_starting_with_dash_does_not_crash_api`

**Recommended fix:** Reject targets starting with '-' or prefix the nmap argument list with '--' before the target.

### VULN-005 -- SSRF (High)
**Endpoint(s):** `POST /scans`

No deny-list exists for internal/loopback/link-local/cloud-metadata address ranges on the `target` field.

**Impact:** If active_testing_enabled is combined with such a target, the scanner could be induced to probe internal infrastructure (including cloud metadata endpoints) on the API's behalf.

**Evidence:** `test_injection.py::TestSsrfStyleTargets (6 parametrized targets, all currently accepted)`

**Recommended fix:** Validate/resolve the target and reject RFC 1918, loopback, link-local, and known cloud-metadata ranges unless explicitly allow-listed per tenant.

### VULN-006 -- Authorization (High)
**Endpoint(s):** `POST /remediations/{rem_id}/mark-executed, POST /vulnerabilities/{vuln_id}/remediations`

mark_remediation_executed() has no role check at all (unlike /approve and /reject, both gated to analyst/admin) -- a client-role user can mark a remediation executed. create_remediation() similarly has no ownership or role restriction, letting any authenticated user trigger a billed AI generation call for a vulnerability they don't own.

**Impact:** Unauthorized state changes to the remediation workflow, and unauthorized consumption of paid AI API calls.

**Evidence:** `test_business_logic.py::test_mark_executed_has_no_role_restriction, test_create_remediation_has_no_ownership_or_role_restriction`

**Recommended fix:** Add the same `if current_user.role not in ['analyst','admin']` guard used elsewhere in remediations.py, plus a scan-ownership check for create_remediation.

### VULN-007 -- Business Logic (Medium)
**Endpoint(s):** `POST /remediations/{rem_id}/approve, POST /remediations/{rem_id}/reject`

Neither endpoint checks the remediation's current status before transitioning it -- an already-APPROVED remediation can be silently REJECTED (or vice versa) with no conflict error and no record of the contradiction.

**Impact:** Audit-trail integrity gap in a security-sensitive approval workflow.

**Evidence:** `test_business_logic.py::test_reject_after_approve_silently_overwrites_state`

**Recommended fix:** Add a state-machine guard: only allow PENDING -> APPROVED/REJECTED transitions, returning 409 Conflict otherwise.

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

### VULN-010 -- Functional Gap (Medium)
**Endpoint(s):** `PATCH /admin/config/{key}`

update_config() returns the submitted value directly without writing to any store, and list_config() returns a hardcoded literal list -- a PATCH call reports success but has zero effect on subsequent GETs.

**Impact:** Administrators would reasonably believe a configuration change took effect when it did not; not a security issue but a significant functional/trust gap.

**Evidence:** `test_functional_api.py::test_patch_config_change_is_not_actually_persisted`

**Recommended fix:** Back /admin/config with a real table (or settings store) and have both endpoints read/write the same source of truth.

## Methodology notes
- All 400 tests in this suite run against a real `uvicorn` process bound to
  an ephemeral SQLite database, not against route handlers called directly
  in-process -- so CORS middleware, JSON parsing, and the real JWT auth
  dependency are all genuinely exercised on every request.
- `nmap` is not available in this environment, so background scan execution
  itself was not (and cannot be) exercised end-to-end here; all scan-related
  tests assert against the synchronous API contract only.
- No live AI (Groq/Gemini) credentials are configured, so remediation
  generation was tested up to the point of the outbound AI call.
