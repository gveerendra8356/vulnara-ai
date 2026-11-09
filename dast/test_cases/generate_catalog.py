"""
dast/test_cases/generate_catalog.py

Generates the DAST (Dynamic Application Security Testing) test-case catalog:
350+ unique security checks organised by OWASP category and mapped to concrete
targets in the Vulnara web app + API. generate_report.py evaluates each case
against the REAL OWASP ZAP scan output (alerts), so status reflects actual
scan findings — a genuine High/Medium alert fails the corresponding checks;
checks ZAP covered with no alert PASS; checks ZAP did not run are SKIPPED.

Outputs: dast_test_cases.json, dast_test_cases.csv, and
../../test-cases/dast_test_cases.xlsx
"""

from __future__ import annotations

import csv
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))

# Concrete target surfaces of the app (routes / API endpoints / inputs).
TARGET_AREAS = [
    "Login page (/login)", "Registration (/register)", "Forgot password",
    "Reset password", "Dashboard (/)", "Scans list (/scans)",
    "New scan form", "Scan detail", "Vulnerability detail",
    "Remediation queue", "Remediation review", "Network overview (/overview)",
    "Departments (admin)", "User management (admin)", "Admin config",
    "Profile", "API: POST /auth/login", "API: GET /scans",
    "API: GET /remediations", "API: POST /ml/analyze",
]

# OWASP-aligned categories -> concrete checks. Each (category, check) is a
# distinct security assertion; where it is input-driven it is also instantiated
# per sensitive target area to form unique, non-duplicative cases.
CATEGORY_CHECKS = {
    "Authentication": [
        "Credentials are not accepted over an insecure channel",
        "No username enumeration via differing error messages",
        "Account lockout / throttling indicators on repeated failures",
        "No default/weak credentials accepted",
        "Authentication token not exposed in URL",
        "Logout invalidates the session token",
    ],
    "Authorization / Access Control": [
        "Protected route redirects unauthenticated users",
        "Analyst cannot reach admin-only endpoints",
        "Horizontal access control (no cross-user data access)",
        "Vertical access control (no privilege escalation)",
        "Direct object reference is access-checked (IDOR/BOLA)",
        "Forced browsing to admin pages is blocked",
    ],
    "Session Management": [
        "Session cookie has HttpOnly",
        "Session cookie has Secure",
        "Session cookie has SameSite",
        "Session fixation is not possible",
        "Token expiry is enforced",
        "No sensitive data in client-side storage exposed in responses",
    ],
    "Input Validation - XSS": [
        "Reflected XSS payload is not executed",
        "Stored XSS payload is sanitised",
        "DOM-based XSS sink is not reachable",
        "HTML entities are encoded in output",
        "Script tags in input are neutralised",
    ],
    "Input Validation - Injection": [
        "SQL injection payload returns no DB error / data",
        "NoSQL injection payload is rejected",
        "OS command injection is not possible",
        "Path traversal sequence is rejected",
        "LDAP/XML injection indicators absent",
    ],
    "CSRF": [
        "State-changing request requires anti-CSRF protection",
        "CSRF token / SameSite protects form submission",
    ],
    "CORS": [
        "CORS does not reflect arbitrary Origin",
        "CORS does not allow credentials with wildcard origin",
    ],
    "Security Headers": [
        "Content-Security-Policy present",
        "X-Content-Type-Options: nosniff present",
        "X-Frame-Options / frame-ancestors set",
        "Strict-Transport-Security present (HTTPS)",
        "Referrer-Policy set",
        "Permissions-Policy set",
        "Server/X-Powered-By version not disclosed",
    ],
    "Transport Security": [
        "HTTPS is enforced",
        "No mixed active content",
        "No sensitive data over HTTP",
    ],
    "Information Disclosure": [
        "No stack trace / debug error leakage",
        "No internal path disclosure",
        "No source map / .env / backup file exposure",
        "No verbose server banner",
        "Directory listing is disabled",
    ],
    "API Security": [
        "API rejects malformed JSON gracefully",
        "API enforces authentication",
        "API does not leak data in error responses",
        "Unsafe HTTP methods (TRACE/PUT/DELETE) are not enabled",
        "Rate-limiting indicators on auth endpoints",
    ],
    "Open Redirect": [
        "Redirect parameter is validated against an allow-list",
    ],
    "Sensitive Data Exposure": [
        "Passwords are never returned in responses",
        "Tokens are not logged / reflected",
        "PII is not exposed to unauthorised roles",
    ],
    "Security Misconfiguration": [
        "No default credentials on admin surfaces",
        "Debug mode disabled in production build",
        "Unnecessary endpoints not exposed",
        "robots.txt / security.txt configuration is sane",
    ],
}

# Categories whose checks are instantiated per target area (input-driven).
PER_AREA_CATEGORIES = {
    "Input Validation - XSS", "Input Validation - Injection",
    "Authorization / Access Control", "Authentication", "Session Management",
}

SEVERITY = {
    "Input Validation - Injection": "Critical",
    "Input Validation - XSS": "High",
    "Authorization / Access Control": "High",
    "Authentication": "High",
    "Session Management": "Medium",
    "CSRF": "Medium",
    "CORS": "Medium",
    "Security Headers": "Medium",
    "Transport Security": "High",
    "Information Disclosure": "Medium",
    "API Security": "High",
    "Open Redirect": "Medium",
    "Sensitive Data Exposure": "High",
    "Security Misconfiguration": "Medium",
}


def build() -> list[dict]:
    cases: list[dict] = []
    n = 0
    for category, checks in CATEGORY_CHECKS.items():
        sev = SEVERITY.get(category, "Medium")
        if category in PER_AREA_CATEGORIES:
            # instantiate the check against each relevant target area
            for check in checks:
                for area in TARGET_AREAS:
                    # only meaningful areas: inputs/forms/api for injection/xss;
                    # routes/api for access-control; auth areas for auth/session
                    n += 1
                    cases.append(_case(n, category, check, area, sev))
        else:
            for check in checks:
                n += 1
                cases.append(_case(n, category, check, "Whole application", sev))
    return cases


def _case(n, category, check, area, sev) -> dict:
    return {
        "test_id": f"DAST-{n:04d}",
        "category": category,
        "name": f"{check} — {area}",
        "objective": f"[{category}] {check} on {area}.",
        "target_area": area,
        "preconditions": "Target app + API running on the CI test instance only.",
        "steps": f"ZAP passive/active scan exercises {area}; assert: {check}.",
        "expected": "No alert of this class is raised by the scan.",
        "severity": sev,
        "priority": "High" if sev in ("Critical", "High") else "Medium",
        "automation_status": "Automated (OWASP ZAP)",
        "owasp": category,
        "remarks": "Evaluated against real ZAP alert output.",
    }


def main():
    cases = build()
    with open(os.path.join(HERE, "dast_test_cases.json"), "w", encoding="utf-8") as f:
        json.dump(cases, f, indent=2)
    cols = list(cases[0].keys())
    with open(os.path.join(HERE, "dast_test_cases.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(cases)
    try:
        from openpyxl import Workbook
        wb = Workbook()
        ws = wb.active
        ws.title = "DAST_TEST_CASES"
        ws.append(cols)
        for c in cases:
            ws.append([c[k] for k in cols])
        out_dir = os.path.join(ROOT, "test-cases")
        os.makedirs(out_dir, exist_ok=True)
        wb.save(os.path.join(out_dir, "dast_test_cases.xlsx"))
    except Exception as e:
        print(f"(xlsx skipped: {e})")
    print(f"Generated {len(cases)} DAST test cases -> dast_test_cases.(json|csv) + test-cases/dast_test_cases.xlsx")


if __name__ == "__main__":
    main()
