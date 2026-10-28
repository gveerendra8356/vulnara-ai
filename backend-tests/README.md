# Vulnara Backend Test Suite

A backend API regression + security test suite for
[`vulnara-ai/backend`](https://github.com/gveerendra8356/vulnara-ai), built
by actually reading the codebase (routes, schemas, models) rather than
guessing at an API contract, and validated by running every single test
against the real, running FastAPI application.

**Last full run (2026-10-28): 404 passed, 0 failed.** Full results are in
`reports/`.

## What's in here

```
backend-tests/
├── conftest.py                  # spins up a real uvicorn instance + ephemeral SQLite DB per run
├── seed_test_accounts.py        # seeds admin/analyst/client1/client2 QA accounts
├── seed_fixture_data.py         # seeds one scan + vulnerability + 2 remediations directly
├── pytest.ini
├── requirements.txt
├── tests/
│   ├── test_authentication.py   # register/login/refresh/logout/me
│   ├── test_authorization.py    # RBAC + cross-tenant access checks
│   ├── test_input_validation.py # schema boundaries and formats
│   ├── test_injection.py        # injection and payload handling
│   ├── test_business_logic.py   # remediation lifecycle and scan cancellation
│   ├── test_configuration.py    # CORS, headers, and rate-limit behavior
│   ├── test_functional_api.py   # API contract coverage
│   ├── test_dast.py             # auth bypass, JWT, and IDOR probes
│   └── test_scan_runtime.py     # AI failure propagation and subprocess cancellation
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
6. Tears the server down. The next run recreates the isolated test database.

Nothing here ever touches a production database or real credentials.

## What generate_reports.py produces

| File | What it is |
|---|---|
| `reports/test-cases.xlsx` | One row per test case: ID, category, title, objective, steps, expected result, severity, **actual pass/fail status from the last run**, duration. Plus a per-category summary sheet. |
| `reports/Automation_Test_Report.xlsx` | Styled to match the sample report you shared — `Executed Tests` / `Passed` / `Failed` / `Skipped` / `Execution Metrics` / `Defect Summary` sheets. |
| `reports/findings.xlsx` | Curated findings with severity, evidence, impact, and recommended fixes. |
| `reports/endpoint-inventory.xlsx` | All 27 REST endpoints + 1 WebSocket, method, auth requirement, description. |
| `reports/backend-inventory.md` | Stack detection: framework, DB, auth mechanism, API surface, environment notes. |
| `reports/executive-summary.md` | Headline numbers and curated follow-up items. |
| `reports/security-review.md` | Summary of curated findings and test methodology. |
| `reports/performance-report.md` | Real latency numbers from a lightweight load sample, plus why full k6 wasn't run here (see below) and how to run it yourself. |

`generate_reports.py` re-parses every test's docstring via Python's `ast`
module (not just whatever ran), so `test-cases.xlsx` documents all collected
cases regardless of which ones executed in a given run, and merges in the
actual pass/fail outcome from `--json-report` when available.

## Corrected regression coverage

Passwords exceeding bcrypt's 72-byte limit are rejected with HTTP 422 for
registration, profile password changes, and admin-created accounts. Tests
assert the validation result rather than treating a server error as expected.

## Findings carried forward (see `findings.xlsx` / `security-review.md`)

| ID | Severity | Summary |
|---|---|---|
| VULN-005 | High | No SSRF deny-list on scan targets (metadata IPs, localhost all accepted). |
| VULN-009 | High | No rate limiting anywhere on `/auth/login` or `/auth/register`. |
| VULN-004 | Medium | A scan target starting with `-` could argument-inject into the `nmap` call. |
| VULN-008 | Low | No security response headers (X-Frame-Options, CSP, etc.) or Server-banner suppression. |

See the evidence column in `findings.xlsx`; accepted-input tests alone do not
prove end-to-end exploitability. No live scan was run as part of this test
suite.

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
