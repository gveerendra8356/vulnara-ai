"""
live-smoke/generate_report.py

Turns the pytest-json-report output of the live GitHub Pages smoke suite into
the required report layout:

  Test Results/
    Excel/Automation_Test_Report.xlsx
    HTML/execution-report.html
    Summary/summary.md

Usage:
  python generate_report.py --json report.json --out "Test Results" \
      --base-url "$BASE_URL" --summary-out "$GITHUB_STEP_SUMMARY"
"""

from __future__ import annotations

import argparse
import json
import os
import time


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="report.json")
    ap.add_argument("--out", default="Test Results")
    ap.add_argument("--base-url", default=os.environ.get("BASE_URL", ""))
    ap.add_argument("--summary-out", default=None)
    args = ap.parse_args()

    data = {}
    if os.path.exists(args.json):
        with open(args.json, encoding="utf-8") as f:
            data = json.load(f)

    tests = data.get("tests", [])
    rows = []
    for t in tests:
        outcome = t.get("outcome", "unknown").upper()
        status = {"PASSED": "PASS", "FAILED": "FAIL", "SKIPPED": "SKIP"}.get(outcome, outcome)
        call = t.get("call", {}) or {}
        msg = ""
        if status == "FAIL":
            msg = str(call.get("longrepr") or t.get("longrepr") or "")[:500]
        rows.append({
            "name": t.get("nodeid", "?").split("::")[-1],
            "nodeid": t.get("nodeid", "?"),
            "status": status,
            "duration": round(call.get("duration", t.get("duration", 0)) or 0, 3),
            "message": msg,
        })

    total = len(rows)
    passed = sum(1 for r in rows if r["status"] == "PASS")
    failed = sum(1 for r in rows if r["status"] == "FAIL")
    skipped = sum(1 for r in rows if r["status"] == "SKIP")
    pass_pct = round(passed / total * 100, 2) if total else 0.0
    ts = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())

    for sub in ("Excel", "HTML", "Screenshots", "Logs", "Summary"):
        os.makedirs(os.path.join(args.out, sub), exist_ok=True)

    # ---- Excel ----
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill
    wb = Workbook()
    head = Font(bold=True, color="FFFFFF")
    fill = PatternFill("solid", fgColor="1F4E78")

    s = wb.active
    s.title = "Summary"
    s.append(["Metric", "Value"])
    for c in s[1]:
        c.font = head
        c.fill = fill
    for k, v in [("Deployment URL", args.base_url), ("Total Tests", total),
                 ("Passed", passed), ("Failed", failed), ("Skipped", skipped),
                 ("Pass Percentage", f"{pass_pct}%"), ("Timestamp", ts)]:
        s.append([k, v])

    r = wb.create_sheet("Test Results")
    r.append(["Test Name", "Node ID", "Status", "Duration (s)", "Failure Reason"])
    for c in r[1]:
        c.font = head
        c.fill = fill
    for x in rows:
        r.append([x["name"], x["nodeid"], x["status"], x["duration"], x["message"]])
    wb.save(os.path.join(args.out, "Excel", "Automation_Test_Report.xlsx"))

    # ---- HTML ----
    tr = "".join(
        f'<tr class="{x["status"].lower()}"><td>{x["name"]}</td><td>{x["status"]}</td>'
        f'<td>{x["duration"]}</td><td><pre>{(x["message"] or "")[:400]}</pre></td></tr>'
        for x in rows)
    html = f"""<!doctype html><html><head><meta charset="utf-8">
<title>Live Pages E2E Report</title><style>
body{{font-family:system-ui,Arial,sans-serif;margin:24px;background:#0a0a0a;color:#e6e9ef}}
table{{border-collapse:collapse;width:100%}}th,td{{border:1px solid #2a2f3a;padding:8px;text-align:left;vertical-align:top}}
th{{background:#1f4e78}}tr.pass td{{background:rgba(42,229,138,.06)}}tr.fail td{{background:rgba(255,107,107,.08)}}
pre{{margin:0;white-space:pre-wrap;font-size:.8em;color:#99a2b2}}.k{{color:#7aa7ff}}
</style></head><body>
<h1>Live GitHub Pages E2E Report</h1>
<p>Deployment: <span class="k">{args.base_url}</span><br>{ts}</p>
<p><b>{passed}/{total}</b> passed ({pass_pct}%) · {failed} failed · {skipped} skipped</p>
<table><tr><th>Test</th><th>Status</th><th>Duration</th><th>Failure reason</th></tr>{tr}</table>
</body></html>"""
    with open(os.path.join(args.out, "HTML", "execution-report.html"), "w", encoding="utf-8") as f:
        f.write(html)

    # ---- summary.md (+ GitHub step summary) ----
    md = ["# Live GitHub Pages E2E Test Summary", "",
          f"Deployment URL:\n{args.base_url}", "",
          f"Total Tests: {total}", f"Passed: {passed}", f"Failed: {failed}",
          f"Skipped: {skipped}", f"Pass Percentage: {pass_pct}%", ""]
    fails = [r for r in rows if r["status"] == "FAIL"]
    if fails:
        md.append("Failed Tests:")
        for r in fails:
            md.append(f"- {r['name']} — {(r['message'].splitlines() or [''])[-1][:160]}")
    md_text = "\n".join(md) + "\n"
    with open(os.path.join(args.out, "Summary", "summary.md"), "w", encoding="utf-8") as f:
        f.write(md_text)
    if args.summary_out:
        with open(args.summary_out, "a", encoding="utf-8") as f:
            f.write(md_text)
    print(md_text)


if __name__ == "__main__":
    main()
