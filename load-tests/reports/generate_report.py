"""
load-tests/reports/generate_report.py

Reads the REAL Locust CSV output (reports/load_stats.csv) + the test-case
catalog and produces the load Excel/HTML/JSON report. Every case's status is
derived from measured statistics evaluated against thresholds.py — nothing is
fabricated. Cases whose endpoint was not exercised are marked SKIPPED, never
PASS.

Gate: the job fails (exit 1) only on a genuine breach — the aggregate error
rate or p95 exceeding the global ceiling, or any High-priority endpoint
exceeding its error-rate/latency threshold.

Usage:  python reports/generate_report.py [--stats reports/load_stats.csv]
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
LOAD_ROOT = os.path.dirname(HERE)
sys.path.insert(0, LOAD_ROOT)

import thresholds  # noqa: E402

CATALOG = os.path.join(LOAD_ROOT, "test_cases", "load_test_cases.json")


def _to_float(v, default=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def load_stats(path: str) -> dict:
    """Parse Locust's stats CSV into {name: {p95, error_rate, rps, count}}."""
    stats = {}
    if not os.path.exists(path):
        return stats
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            name = (row.get("Name") or "").strip()
            typ = (row.get("Type") or "").strip()
            if not name:
                continue
            key = name if typ in ("", "Aggregated") else f"{typ} {name}".strip()
            count = _to_float(row.get("Request Count"))
            fails = _to_float(row.get("Failure Count"))
            p95 = _to_float(row.get("95%") or row.get("95%ile") or row.get("Max Response Time"))
            rps = _to_float(row.get("Requests/s"))
            entry = {
                "p95": p95,
                "error_rate": (fails / count * 100.0) if count else 0.0,
                "rps": rps,
                "count": count,
            }
            stats[key] = entry
            stats[name] = entry  # also index by bare name
    return stats


def match_stats(endpoint: str, stats: dict) -> dict | None:
    if endpoint in ("mixed", "Robustness"):
        return stats.get("Aggregated")
    # locust groups POST/GET into "Type"+"Name"; our endpoint strings already
    # carry the verb, so try exact then bare-name.
    if endpoint in stats:
        return stats[endpoint]
    bare = endpoint.split(" ", 1)[-1]
    return stats.get(bare)


def evaluate(cases: list[dict], stats: dict):
    agg = stats.get("Aggregated", {})
    results = []
    for c in cases:
        # "mixed" (system-level) cases evaluate the aggregate; concrete-endpoint
        # cases evaluate only their own measured stats. An endpoint that was
        # never exercised is SKIPPED, never silently promoted to PASS.
        st = stats.get("Aggregated") if c["endpoint"] == "mixed" else match_stats(c["endpoint"], stats)
        th = thresholds.threshold_for(c["endpoint"] if c["endpoint"] != "mixed" else "")
        status, actual = "SKIPPED", "n/a (endpoint not exercised)"
        if st and st.get("count", 0) > 0:
            metric = c["metric"]
            if metric.startswith("Response time"):
                actual = f"p95={st['p95']:.0f}ms (<= {th['p95_ms']}ms)"
                status = "PASSED" if st["p95"] <= th["p95_ms"] else "FAILED"
            elif metric == "Error rate":
                actual = f"errors={st['error_rate']:.2f}% (<= {th['max_error_rate']}%)"
                status = "PASSED" if st["error_rate"] <= th["max_error_rate"] else "FAILED"
            else:  # Throughput
                actual = f"{st['rps']:.2f} req/s over {st['count']:.0f} requests"
                status = "PASSED" if st["rps"] > 0 else "FAILED"
        r = dict(c)
        r["actual_result"] = actual
        r["status"] = status
        results.append(r)
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stats", default=os.path.join(HERE, "load_stats.csv"))
    ap.add_argument("--commit", default=os.environ.get("GITHUB_SHA", "local"))
    args = ap.parse_args()

    with open(CATALOG, encoding="utf-8") as f:
        cases = json.load(f)
    stats = load_stats(args.stats)
    results = evaluate(cases, stats)

    total = len(results)
    passed = sum(1 for r in results if r["status"] == "PASSED")
    failed = sum(1 for r in results if r["status"] == "FAILED")
    skipped = sum(1 for r in results if r["status"] == "SKIPPED")
    executed = passed + failed
    pass_rate = round(passed / executed * 100, 2) if executed else 0.0

    agg = stats.get("Aggregated", {"error_rate": 0.0, "p95": 0.0, "rps": 0.0, "count": 0})
    # Genuine gate: aggregate breach or any High-priority endpoint failure.
    gate_breaches = []
    if agg.get("count", 0) == 0:
        gate_breaches.append("no requests were recorded (backend unreachable?)")
    if agg.get("error_rate", 0) > thresholds.GLOBAL_MAX_ERROR_RATE:
        gate_breaches.append(f"aggregate error rate {agg['error_rate']:.2f}% > {thresholds.GLOBAL_MAX_ERROR_RATE}%")
    if agg.get("p95", 0) > thresholds.GLOBAL_P95_CEILING_MS:
        gate_breaches.append(f"aggregate p95 {agg['p95']:.0f}ms > {thresholds.GLOBAL_P95_CEILING_MS}ms")
    high_fail = [r["test_id"] for r in results if r["status"] == "FAILED" and r.get("priority") == "High"]
    if high_fail:
        gate_breaches.append(f"{len(high_fail)} High-priority performance checks failed")

    deployment_ready = "PASS" if not gate_breaches else "FAIL"

    # ---- Excel ----
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill

    wb = Workbook()
    head = Font(bold=True, color="FFFFFF")
    head_fill = PatternFill("solid", fgColor="1F4E78")

    s = wb.active
    s.title = "SUMMARY"
    summary_rows = [
        ("Total Tests", total), ("Passed", passed), ("Failed", failed),
        ("Skipped", skipped), ("Pass Percentage", f"{pass_rate}%"),
        ("Category", "Performance / Load (Locust)"),
        ("Environment", os.environ.get("LOAD_BASE_URL", "http://127.0.0.1:8000")),
        ("Build/Commit", args.commit),
        ("Aggregate requests", int(agg.get("count", 0))),
        ("Aggregate p95 (ms)", round(agg.get("p95", 0), 1)),
        ("Aggregate error rate (%)", round(agg.get("error_rate", 0), 2)),
        ("Aggregate throughput (req/s)", round(agg.get("rps", 0), 2)),
        ("Timestamp", time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())),
        ("Deployment Readiness", deployment_ready),
    ]
    s.append(["Metric", "Value"])
    for cell in s[1]:
        cell.font = head
        cell.fill = head_fill
    for k, v in summary_rows:
        s.append([k, v])

    r = wb.create_sheet("TEST RESULTS")
    cols = ["Test ID", "Test Category", "Test Name", "Objective", "Scenario",
            "Endpoint", "Users", "Spawn Rate", "Duration", "Expected Result",
            "Actual Result", "Status", "Priority", "Automation Status", "Remarks"]
    r.append(cols)
    for cell in r[1]:
        cell.font = head
        cell.fill = head_fill
    for x in results:
        r.append([x["test_id"], x["category"], x["name"], x["objective"], x["scenario"],
                  x["endpoint"], x["users"], x["spawn_rate"], x["duration"], x["expected"],
                  x["actual_result"], x["status"], x["priority"], x["automation_status"], x["remarks"]])

    perf = wb.create_sheet("PERFORMANCE")
    perf.append(["Endpoint", "Requests", "p95 (ms)", "Error rate (%)", "Throughput (req/s)"])
    for cell in perf[1]:
        cell.font = head
        cell.fill = head_fill
    seen = set()
    for name, st in stats.items():
        if name in seen or st.get("count", 0) == 0:
            continue
        seen.add(name)
        perf.append([name, int(st["count"]), round(st["p95"], 1),
                     round(st["error_rate"], 2), round(st["rps"], 2)])

    out_xlsx = os.path.join(HERE, "load_report.xlsx")
    wb.save(out_xlsx)

    # ---- JSON + markdown summary ----
    with open(os.path.join(HERE, "load_report.json"), "w", encoding="utf-8") as f:
        json.dump({"total": total, "passed": passed, "failed": failed, "skipped": skipped,
                   "pass_rate": pass_rate, "aggregate": agg, "deployment_ready": deployment_ready,
                   "gate_breaches": gate_breaches, "results": results}, f, indent=2)

    md = [
        "# Load / Performance Test Summary", "",
        f"- **Total cases:** {total}  |  **Passed:** {passed}  |  **Failed:** {failed}  |  **Skipped:** {skipped}",
        f"- **Pass rate (executed):** {pass_rate}%",
        f"- **Requests:** {int(agg.get('count', 0))}  |  **p95:** {agg.get('p95', 0):.0f}ms  "
        f"|  **Error rate:** {agg.get('error_rate', 0):.2f}%  |  **Throughput:** {agg.get('rps', 0):.2f} req/s",
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
        print("::error::Load gate failed: " + "; ".join(gate_breaches))
        sys.exit(1)


if __name__ == "__main__":
    main()
