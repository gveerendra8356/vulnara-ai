# DAST Security Testing (OWASP ZAP)

Dynamic security scanning runs **only against the web application**, served
locally on the CI runner — never a third-party system, and non-destructive
(ZAP baseline: passive + safe spidering).

## Layout
- `test_cases/generate_catalog.py` — generates the 350+ case catalog across OWASP categories (`dast_test_cases.json/csv` + `test-cases/dast_test_cases.xlsx`).
- `reports/generate_report.py` — reads the **real** ZAP JSON report, maps alerts onto the catalog, writes `dast_report.xlsx/json` + `summary.md`, and **fails the job on any genuine High-risk alert**. Medium/Low/Info alerts are reported (SECURITY_ALERTS sheet) but do not block — a documented, CI-friendly policy. Nothing is converted to PASS.

## CI flow (see `.github/workflows/deploy.yml`, the `dast-security-tests` job)
1. Build the web app (Mock Mode) and serve it on `:4173` with security headers.
2. Run `zaproxy/action-baseline` against the served site (`fail_action: false`, `allow_issue_writing: false`).
3. Convert `report_json.json` → Excel/JSON report and apply the High-risk gate.

> Note: GitHub Pages cannot send custom response headers, so the security
> headers are applied to the **CI test instance** being scanned. The app's
> defence-in-depth headers belong at the backend/CDN layer in a real
> deployment.
