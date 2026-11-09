"""
dast/reports/generate_report.py

Reads the REAL OWASP ZAP JSON report + the DAST catalog and produces the
security Excel/HTML/JSON report. Each catalog case's status is derived from
actual ZAP alerts:

  * ZAP produced a report and no alert of the case's category was raised  -> PASSED
  * an alert of the case's category was raised at Medium+ risk            -> FAILED
  * ZAP did not run / produced no report                                  -> SKIPPED

Gate: the job fails (exit 1) on any genuine High-risk (riskcode 3) ZAP alert.
Medium/Low/Informational alerts are reported as findings but do not block the
pipeline (documented, CI-friendly policy). Nothing is converted to PASS.

Usage:  python reports/generate_report.py --zap reports/zap_report.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
DAST_ROOT = os.path.dirname(HERE)
CATALOG = os.path.join(DAST_ROOT, "test_cases", "dast_test_cases.json")

RISK_NAME = {0: "Informational", 1: "Low", 2: "Medium", 3: "High"}

# Map catalog categories to substrings that appear in ZAP alert names.
CATEGORY_KEYWORDS = {
    "Authentication": ["authentication", "password", "login", "credential"],
    "Authorization / Access Control": ["access control", "authorization", "idor", "directory browsing"],
    "Session Management": ["cookie", "httponly", "samesite", "secure flag", "session"],
    "Input Validation - XSS": ["cross site scripting", "xss"],
    "Input Validation - Injection": ["sql injection", "injection", "remote code", "path traversal", "command"],
    "CSRF": ["csrf", "anti-csrf", "cross-site request"],
    "CORS": ["cors", "cross-domain", "cross domain"],
    "Security Headers": ["content security policy", "csp", "x-content-type", "x-frame",
                          "strict-transport", "anti-clickjacking", "referrer", "permissions policy",
                          "x-powered", "server leaks"],
    "Transport Security": ["https", "mixed content", "transport", "tls", "ssl"],
    "Information Disclosure": ["information disclosure", "error", "stack trace", "timestamp",
                               "suspicious comment", "debug", "source"],
    "API Security": ["method", "json", "api"],
    "Open Redirect": ["redirect"],
    "Sensitive Data Exposure": ["sensitive", "private ip", "hash", "credit card", "email"],
    "Security Misconfiguration": ["misconfiguration", "default", "robots", "directory browsing"],
}


def load_zap(path: str):
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    alerts = []
    for site in data.get("site", []):
        for a in site.get("alerts", []):
            try:
                risk = int(a.get("riskcode", 0))
            except (TypeError, ValueError):
                risk = 0
            alerts.append({
                "name": (a.get("name") or a.get("alert") or "").strip(),
                "risk": risk,
                "confidence": a.get("confidence"),
                "count": int(a.get("count", len(a.get("instances", [])) or 1)),
                "desc": (a.get("desc") or "").strip()[:300],
            })
    return alerts


def category_has_alert(category: str, alerts: list, min_risk: int = 2):
    kws = CATEGORY_KEYWORDS.get(category, [])
    for a in alerts:
        if a["risk"] >= min_risk and any(k in a["name"].lower() for k in kws):
            return a
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--zap", default=os.path.join(HERE, "zap_report.json"))
    ap.add_argument("--commit", default=os.environ.get("GITHUB_SHA", "local"))
    ap.add_argument("--target", default=os.environ.get("DAST_TARGET", "CI test instance"))
    args = ap.parse_args()

    with open(CATALOG, encoding="utf-8") as f:
        cases = json.load(f)
    alerts = load_zap(args.zap)

    results = []
    for c in cases:
        if alerts is None:
            status, actual = "SKIPPED", "ZAP produced no report"
        else:
            hit = category_has_alert(c["category"], alerts)
            if hit:
                status = "FAILED"
                actual = f"ZAP alert: {hit['name']} ({RISK_NAME.get(hit['risk'])}, x{hit['count']})"
            else:
                status = "PASSED"
                actual = "No alert of this class raised by the scan"
        r = dict(c)
        r["actual_result"] = actual
        r["status"] = status
        results.append(r)

    total = len(results)
    passed = sum(1 for r in results if r["status"] == "PASSED")
    failed = sum(1 for r in results if r["status"] == "FAILED")
    skipped = sum(1 for r in results if r["status"] == "SKIPPED")
    executed = passed + failed
    pass_rate = round(passed / executed * 100, 2) if executed else 0.0

    # Alert tallies by risk (real ZAP output).
    tally = {"High": 0, "Medium": 0, "Low": 0, "Informational": 0}
    for a in (alerts or []):
        tally[RISK_NAME.get(a["risk"], "Informational")] += 1
    high_alerts = [a for a in (alerts or []) if a["risk"] == 3]

    gate_breaches = []
    if alerts is None:
        gate_breaches.append("ZAP produced no report (scan did not run)")
    if high_alerts:
        gate_breaches.append(f"{len(high_alerts)} High-risk ZAP alert(s): "
                             + ", ".join(sorted({a['name'] for a in high_alerts})))
    deployment_ready = "PASS" if not gate_breaches else "FAIL"

    # ---- Excel ----
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill
    wb = Workbook()
    head = Font(bold=True, color="FFFFFF")
    head_fill = PatternFill("solid", fgColor="7B1E1E")

    s = wb.active
    s.title = "SUMMARY"
    s.append(["Metric", "Value"])
    for cell in s[1]:
        cell.font = head
        cell.fill = head_fill
    for k, v in [
        ("Total Tests", total), ("Passed", passed), ("Failed", failed),
        ("Skipped", skipped), ("Pass Percentage", f"{pass_rate}%"),
        ("Category", "DAST Security (OWASP ZAP)"),
        ("Environment", args.target), ("Build/Commit", args.commit),
        ("High alerts", tally["High"]), ("Medium alerts", tally["Medium"]),
        ("Low alerts", tally["Low"]), ("Informational alerts", tally["Informational"]),
        ("Timestamp", time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())),
        ("Deployment Readiness", deployment_ready),
    ]:
        s.append([k, v])

    rs = wb.create_sheet("TEST RESULTS")
    cols = ["Test ID", "Category", "Test Name", "Objective", "Target Area",
            "Preconditions", "Steps", "Expected Result", "Actual Result",
            "Status", "Severity", "Priority", "Automation Status", "Remarks"]
    rs.append(cols)
    for cell in rs[1]:
        cell.font = head
        cell.fill = head_fill
    for x in results:
        rs.append([x["test_id"], x["category"], x["name"], x["objective"], x["target_area"],
                   x["preconditions"], x["steps"], x["expected"], x["actual_result"],
                   x["status"], x["severity"], x["priority"], x["automation_status"], x["remarks"]])

    al = wb.create_sheet("SECURITY_ALERTS")
    al.append(["Alert", "Risk", "Confidence", "Instances", "Description"])
    for cell in al[1]:
        cell.font = head
        cell.fill = head_fill
    for a in sorted((alerts or []), key=lambda x: -x["risk"]):
        al.append([a["name"], RISK_NAME.get(a["risk"]), a["confidence"], a["count"], a["desc"]])

    wb.save(os.path.join(HERE, "dast_report.xlsx"))

    with open(os.path.join(HERE, "dast_report.json"), "w", encoding="utf-8") as f:
        json.dump({"total": total, "passed": passed, "failed": failed, "skipped": skipped,
                   "pass_rate": pass_rate, "alert_tally": tally, "deployment_ready": deployment_ready,
                   "gate_breaches": gate_breaches}, f, indent=2)

    md = [
        "# DAST Security Test Summary", "",
        f"- **Total cases:** {total}  |  **Passed:** {passed}  |  **Failed:** {failed}  |  **Skipped:** {skipped}",
        f"- **Pass rate (executed):** {pass_rate}%",
        f"- **ZAP alerts** — High: {tally['High']}, Medium: {tally['Medium']}, Low: {tally['Low']}, Info: {tally['Informational']}",
        f"- **Deployment Readiness:** {'✅ PASS' if deployment_ready == 'PASS' else '❌ FAIL'}",
        "",
    ]
    if gate_breaches:
        md.append("### Gate breaches")
        md += [f"- {b}" for b in gate_breaches]
    with open(os.path.join(HERE, "summary.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")
    print("\n".join(md))

    if gate_breaches:
        print("::error::DAST gate failed: " + "; ".join(gate_breaches))
        sys.exit(1)


if __name__ == "__main__":
    main()
