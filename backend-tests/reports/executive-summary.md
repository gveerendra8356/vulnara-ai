# Executive Summary -- Vulnara Backend QA & Security Regression

**Run date:** 2026-08-14
**Scope:** Full backend API (`vulnara-ai/backend`), tested end to end against
a real running instance -- authentication, authorization, input validation,
injection resistance, business logic, configuration, functional correctness,
and dynamic security (DAST) checks.

## Headline numbers
| Metric | Value |
|---|---|
| Total test cases | 400 |
| Passed | 399 |
| Failed | 1 |
| Pass rate | 99.8% |
| Confirmed findings | 10 |
| &nbsp;&nbsp;Critical | 2 |
| &nbsp;&nbsp;High | 3 |
| &nbsp;&nbsp;Medium | 3 |
| &nbsp;&nbsp;Low | 2 |

## What this tells us
The core security controls that matter most are working: SQL injection,
command injection, path traversal, and JWT forgery/tampering were all tried
against every relevant field and endpoint, and every attempt was correctly
rejected. Authentication, token refresh/revocation, and the primary
scan-ownership authorization checks all behave as designed.

That said, this run surfaced **10 confirmed issues**, most
importantly:

- **VULN-001 (Critical):** `GET /vulnerabilities/{id}` and
  `GET /remediations/{id}` have no cross-tenant ownership check at all --
  any logged-in user can read another customer's vulnerability/remediation
  data by ID.
- **VULN-002 (Critical):** Registering with an unusually long password
  crashes the server with a 500 instead of a clean validation error.
- **VULN-006 (High):** `POST /remediations/{id}/mark-executed` has no
  role check -- a client-role user can mark a remediation as executed.
- **VULN-005 (High) / VULN-009 (High):** No SSRF-range restriction on scan
  targets, and no rate limiting anywhere on login/registration.

Full technical detail, evidence, and recommended fixes for every finding are
in `findings.xlsx` and `security-review.md`. Every finding above is backed
by a specific, reproducible automated test in this suite -- re-running
`pytest` after a fix should flip the corresponding test's outcome, which is
called out explicitly in each test's assertion message.

## Recommendation
None of the findings above require blocking a release outright, but
VULN-001, VULN-002, and VULN-006 should be treated as should-fix-before-next-release
given they're all reachable by any authenticated user with no special
tooling. The rest are reasonable backlog items.
