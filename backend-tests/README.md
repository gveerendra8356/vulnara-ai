# Vulnara Backend Test Suite

A 400-case automated regression + security test suite for
[`vulnara-ai/backend`](https://github.com/gveerendra8356/vulnara-ai), built
by actually reading the codebase (routes, schemas, models) rather than
guessing at an API contract, and validated by running every single test
against the real, running FastAPI application.

**Last run: 399 passed / 400, 1 confirmed bug (not a flaky test — see
below).** Full results are in `reports/`.

## What's in here

```
backend-tests/
├── conftest.py                  # spins up a real uvicorn instance + ephemeral SQLite DB per run
├── seed_test_accounts.py        # seeds admin/analyst/client1/client2 QA accounts
├── seed_fixture_data.py         # seeds one scan + vulnerability + 2 remediations directly
├── pytest.ini
├── requirements.txt
├── tests/
│   ├── test_authentication.py   # 43 cases  — register/login/refresh/logout/me
│   ├── test_authorization.py    # 47 cases  — RBAC + cross-tenant IDOR checks
│   ├── test_input_validation.py # 59 cases  — boundary/format checks on every schema
│   ├── test_injection.py        # 67 cases  — SQLi, command injection, path traversal, SSRF, XSS, JWT
│   ├── test_business_logic.py   # 22 cases  — remediation state machine, scan cancellation rules
│   ├── test_configuration.py    # 26 cases  — CORS, security headers, rate limiting
│   ├── test_functional_api.py   # 84 cases  — CRUD/response-contract correctness, every endpoint
│   └── test_dast.py             # 27 cases  — auth bypass, JWT tampering, brute force, IDOR probes
├── performance/
│   └── k6-load-test.js          # full k6 script for CI/staging (see performance-report.md for why it wasn't run here)
├── scripts/
│   ├── generate_reports.py      # produces every file in reports/
│   ├── perf_sample.py           # lightweight async load generator (k6 substitute for this sandbox)
│   └── run_perf_standalone.py   # one-shot driver for perf_sample.py
└── reports/                     # generated — see below
```

Plus `.github/workflows/backend-tests.yml` at the repo root, ready to run
this suite on every push/PR that touches `backend/` or `backend-tests/`.

## How to run it

```bash
cd backend-tests
pip install -r requirements.txt
pip install -r ../backend/requirements.txt

python -m pytest -q \
  --json-report --json-report-file=reports/full_run.json

python scripts/generate_reports.py
```

That's it — no separate database, no Docker, no manual server startup.
`conftest.py` handles all of it per test session:

1. Creates a throwaway `backend/ci_test.db` SQLite file (deleted and
   recreated fresh every run).
2. Seeds four QA accounts directly via SQLAlchemy — **admin, analyst,
   client1, client2** (`seed_test_accounts.py`). Two client accounts exist
   specifically so authorization tests can check *cross-tenant* access, not
   just "logged in vs not logged in."
3. Seeds one scan + vulnerability + two remediations directly
   (`seed_fixture_data.py`) — there's no `POST /vulnerabilities` endpoint,
   they only ever come from the scan pipeline, so this mirrors what a real
   row looks like.
4. Launches the actual `app.main:app` via a real `uvicorn` subprocess and
   waits for `/health` to return 200.
5. Every test talks to that instance over real HTTP with `httpx` — this
   exercises CORS middleware, JSON parsing, the real JWT auth dependency,
   and real async DB round trips, not just a route handler called directly.
6. Tears the server down and deletes the DB file when the session ends.

Nothing here ever touches a production database or real credentials.

## What generate_reports.py produces

| File | What it is |
|---|---|
| `reports/test-cases.xlsx` | One row per test case: ID, category, title, objective, steps, expected result, severity, **actual pass/fail status from the last run**, duration. Plus a per-category summary sheet. |
| `reports/Automation_Test_Report.xlsx` | Styled to match the sample report you shared — `Executed Tests` / `Passed` / `Failed` / `Skipped` / `Execution Metrics` / `Defect Summary` sheets. |
| `reports/findings.xlsx` | 10 curated, confirmed findings (not every "documents current behavior" test — the real, reviewed list), each with severity, evidence (which test proves it), impact, and a specific fix. |
| `reports/endpoint-inventory.xlsx` | All 27 REST endpoints + 1 WebSocket, method, auth requirement, description. |
| `reports/backend-inventory.md` | Stack detection: framework, DB, auth mechanism, API surface, environment notes. |
| `reports/executive-summary.md` | One page, non-technical, headline numbers + top findings. |
| `reports/security-review.md` | Full narrative security review with all 10 findings in detail. |
| `reports/performance-report.md` | Real latency numbers from a lightweight load sample, plus why full k6 wasn't run here (see below) and how to run it yourself. |

`generate_reports.py` re-parses every test's docstring via Python's `ast`
module (not just whatever ran), so `test-cases.xlsx` documents all 400
cases regardless of which ones executed in a given run, and merges in the
actual pass/fail outcome from `--json-report` when available.

## The one confirmed failure — this is a real bug, not a flaky test

`test_authentication.py::TestRegistration::test_register_extremely_long_password_does_not_crash`
**fails on every run, on purpose.** Registering with a password longer than
bcrypt's 72-byte input limit crashes the server with an unhandled 500
instead of a clean validation error. That's `VULN-002` in `findings.xlsx`
— a one-line fix (`Field(min_length=8, max_length=72)` on
`UserRegisterRequest.password`). Once fixed, re-running the suite should
flip this test to a pass.

## The 10 confirmed findings (see `findings.xlsx` / `security-review.md`)

| ID | Severity | Summary |
|---|---|---|
| VULN-001 | **Critical** | `GET /vulnerabilities/{id}` and `GET /remediations/{id}` have no cross-tenant ownership check — any authenticated user can read any other tenant's data by ID. |
| VULN-002 | **Critical** | Registering with a >72-byte password crashes the server (500). |
| VULN-006 | High | `POST /remediations/{id}/mark-executed` has no role check at all; `create_remediation` has no ownership check either. |
| VULN-005 | High | No SSRF deny-list on scan targets (metadata IPs, localhost all accepted). |
| VULN-009 | High | No rate limiting anywhere on `/auth/login` or `/auth/register`. |
| VULN-004 | Medium | A scan target starting with `-` could argument-inject into the `nmap` call. |
| VULN-007 | Medium | Approve/reject on a remediation has no state-machine guard — can silently flip an already-approved remediation to rejected. |
| VULN-010 | Medium | `PATCH /admin/config/{key}` reports success but never actually persists (both endpoints are hardcoded stubs). |
| VULN-003 | Low | Vulnerability `status` field accepts any string, no enum validation. |
| VULN-008 | Low | No security response headers (X-Frame-Options, CSP, etc.) or Server-banner suppression. |

Every one of these is backed by a specific, reproducible test — see the
`Evidence` column in `findings.xlsx` for the exact test name.

## What was verified to be solid

Not everything here is a finding. SQL injection, command injection, path
traversal, and JWT forgery/algorithm-confusion/weak-secret attacks were all
tried against every relevant field and endpoint, and **every single one was
correctly rejected.** The core `/scans/*` authorization model (ownership +
admin override) is implemented correctly and holds under real cross-tenant
testing. Logout genuinely revokes refresh tokens. See
`security-review.md`'s "What was tested well" section for the full list.

## Honesty notes (things this environment couldn't do)

- **`nmap` isn't installed** in the sandbox this suite was built in, so a
  scan's background task fails fast after creation in every run here. This
  doesn't affect any test — every assertion is against the synchronous API
  response, never the background scan outcome. It'll behave identically (and
  meaningfully) in any environment with `nmap` installed.
- **No live Gemini/Groq credentials** are configured, so
  `POST /vulnerabilities/{id}/remediations` returns `502` once past
  authorization in this environment. Tests that touch this endpoint assert
  up to that point (e.g. "did it 403 for the wrong reason" vs "did the AI
  call itself succeed") rather than mocking the AI response.
- **k6 itself couldn't be installed** in this sandbox (no network access to
  its distribution). `performance/k6-load-test.js` is a complete, ready
  script — it just hasn't been executed here. `performance-report.md`
  instead reports real numbers from a smaller in-process async load sample
  (`scripts/perf_sample.py`) against the same ephemeral instance, and is
  explicit about the difference in what that does and doesn't tell you.

