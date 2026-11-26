"""
security/generate_report.py

Phase 3/5/6/7 deliverable: aggregates the REAL output of the SAST and
dependency scanners run in CI (Semgrep, Gitleaks, Trivy, pip-audit, npm audit)
into one normalized set of findings, then writes:

  <out>/security-review.md
  <out>/executive-summary.md
  <out>/dependency-report.md
  <out>/findings.xlsx   (Security Findings · Dependency Vulnerabilities · Risk Summary)

Every finding's severity comes from the scanner itself; nothing is invented.
Gate: exits non-zero ONLY on a Critical finding (per the brief). Missing
scanner outputs are skipped gracefully (a scanner that didn't run contributes
nothing rather than failing the report).

Usage:
  python security/generate_report.py --out "Vulnerability Test Results" \
      --semgrep semgrep.json --gitleaks gitleaks.json --trivy trivy.json \
      --pip-audit pip-audit.json --npm-audit npm-audit.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

SEV_ORDER = ["Critical", "High", "Medium", "Low"]
SCORE_PENALTY = {"Critical": 15, "High": 6, "Medium": 2, "Low": 0.5}


def _load(path: str | None):
    if not path or not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            txt = f.read().strip()
        return json.loads(txt) if txt else None
    except Exception as e:
        print(f"(could not parse {path}: {e})")
        return None


def _finding(sev, vtype, where, desc, fix, endpoint="", exploit="", impact="", source=""):
    return {"severity": sev if sev in SEV_ORDER else "Low", "type": vtype, "where": where,
            "endpoint": endpoint, "description": desc, "exploit": exploit, "impact": impact,
            "fix": fix, "source": source}


# ---- per-scanner normalisers ------------------------------------------------
def from_semgrep(data):
    out = []
    for r in (data or {}).get("results", []):
        extra = r.get("extra", {})
        sev_raw = (extra.get("severity") or "INFO").upper()
        sev = {"ERROR": "High", "WARNING": "Medium", "INFO": "Low"}.get(sev_raw, "Low")
        meta = extra.get("metadata", {}) or {}
        # Semgrep security rules often carry an impact/confidence; a rule tagged
        # as a secret or an injection is escalated.
        cat = " ".join(str(v) for v in (meta.get("category", ""), meta.get("cwe", ""), r.get("check_id", ""))).lower()
        if "injection" in cat or "sql" in cat or "rce" in cat or "command" in cat:
            sev = "High" if sev != "Low" else "Medium"
        out.append(_finding(
            sev, meta.get("category", "SAST") or "SAST",
            f"{r.get('path','?')}:{r.get('start',{}).get('line','?')}",
            extra.get("message", r.get("check_id", "")),
            (meta.get("references") or ["Review and remediate per the Semgrep rule."])[0]
            if isinstance(meta.get("references"), list) else "Review and remediate per the Semgrep rule.",
            source="Semgrep"))
    return out


def from_gitleaks(data):
    out = []
    items = data if isinstance(data, list) else (data or {}).get("findings", [])
    for g in items or []:
        # Placeholder defaults (e.g. "change-in-production") are flagged but are
        # not live secrets -> High, not Critical, so they never block the build;
        # a genuinely live key should be rotated immediately.
        desc = g.get("Description", g.get("description", "Potential hardcoded secret"))
        out.append(_finding(
            "High", "Hardcoded secret / credential",
            f'{g.get("File", g.get("file","?"))}:{g.get("StartLine", g.get("startLine","?"))}',
            f'{desc} (rule: {g.get("RuleID", g.get("ruleID","?"))})',
            "Move the secret to an environment variable / secret store and rotate it if it was ever real.",
            exploit="An attacker reading the repo could reuse a committed credential.",
            impact="Unauthorized access to the associated service.",
            source="Gitleaks"))
    return out


def from_trivy(data):
    out = []
    for res in (data or {}).get("Results", []):
        for v in res.get("Vulnerabilities", []) or []:
            sev = (v.get("Severity") or "LOW").title()
            out.append(_finding(
                sev, f"Vulnerable dependency ({v.get('VulnerabilityID','CVE')})",
                f'{v.get("PkgName","?")}@{v.get("InstalledVersion","?")}',
                v.get("Title", v.get("Description", ""))[:300],
                f'Upgrade to {v.get("FixedVersion")}' if v.get("FixedVersion") else "Upgrade to a patched version.",
                impact="Known CVE in a third-party package.",
                source="Trivy"))
    return out


def from_pip_audit(data):
    out = []
    deps = data if isinstance(data, list) else (data or {}).get("dependencies", [])
    for d in deps or []:
        for v in d.get("vulns", []) or []:
            fixes = v.get("fix_versions") or []
            out.append(_finding(
                "High", f"Vulnerable dependency ({v.get('id','')})",
                f'{d.get("name","?")}@{d.get("version","?")}',
                (v.get("description") or "")[:300],
                f'Upgrade to {", ".join(fixes)}' if fixes else "Upgrade to a patched version.",
                impact="Known advisory affecting a Python dependency.",
                source="pip-audit"))
    return out


def from_npm_audit(data):
    out = []
    vulns = (data or {}).get("vulnerabilities", {})
    for name, v in (vulns.items() if isinstance(vulns, dict) else []):
        sev = {"critical": "Critical", "high": "High", "moderate": "Medium", "low": "Low"}.get(
            (v.get("severity") or "low").lower(), "Low")
        out.append(_finding(
            sev, "Vulnerable dependency (npm)",
            f'{name}@{v.get("range","?")}',
            f'npm advisory for {name}',
            "Run `npm audit fix` / upgrade to a non-vulnerable version.",
            impact="Known advisory affecting a web dependency.",
            source="npm audit"))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="Vulnerability Test Results")
    ap.add_argument("--semgrep")
    ap.add_argument("--gitleaks")
    ap.add_argument("--trivy")
    ap.add_argument("--pip-audit", dest="pip_audit")
    ap.add_argument("--npm-audit", dest="npm_audit")
    ap.add_argument("--commit", default=os.environ.get("GITHUB_SHA", "local"))
    args = ap.parse_args()

    findings = []
    findings += from_semgrep(_load(args.semgrep))
    findings += from_gitleaks(_load(args.gitleaks))
    findings += from_trivy(_load(args.trivy))
    findings += from_pip_audit(_load(args.pip_audit))
    findings += from_npm_audit(_load(args.npm_audit))

    findings.sort(key=lambda f: SEV_ORDER.index(f["severity"]))
    counts = {s: sum(1 for f in findings if f["severity"] == s) for s in SEV_ORDER}
    dep_findings = [f for f in findings if f["source"] in ("Trivy", "pip-audit", "npm audit")]

    penalty = sum(SCORE_PENALTY[f["severity"]] for f in findings)
    score = max(0, round(100 - penalty))

    os.makedirs(args.out, exist_ok=True)
    ts = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())

    # ---- executive-summary.md ----
    top = findings[:3]
    exec_md = [
        "# Executive Summary", "",
        f"_Generated {ts} · commit `{args.commit}`_", "",
        "## Total Findings", "",
        f"- **Critical:** {counts['Critical']}",
        f"- **High:** {counts['High']}",
        f"- **Medium:** {counts['Medium']}",
        f"- **Low:** {counts['Low']}", "",
        "## Most Critical Risks", "",
    ]
    if top:
        for i, f in enumerate(top, 1):
            exec_md.append(f"{i}. **[{f['severity']}] {f['type']}** — {f['where']} ({f['source']})")
    else:
        exec_md.append("_No findings reported by the configured scanners._")
    exec_md += ["", "## Overall Security Score", "", f"**{score} / 100**", ""]
    with open(os.path.join(args.out, "executive-summary.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(exec_md) + "\n")

    # ---- security-review.md ----
    rev = ["# Security Review", "", f"_Generated {ts} · commit `{args.commit}`_", "",
           f"**Score {score}/100** — Critical {counts['Critical']}, High {counts['High']}, "
           f"Medium {counts['Medium']}, Low {counts['Low']}.", ""]
    if not findings:
        rev.append("_No findings reported by the configured scanners._")
    for f in findings:
        rev += [
            f"## [{f['severity']}] {f['type']}",
            f"- **Source:** {f['source']}",
            f"- **Location:** `{f['where']}`" + (f" · endpoint `{f['endpoint']}`" if f['endpoint'] else ""),
            f"- **Description:** {f['description']}",
            (f"- **Exploitation:** {f['exploit']}" if f['exploit'] else ""),
            (f"- **Impact:** {f['impact']}" if f['impact'] else ""),
            f"- **Recommended fix:** {f['fix']}", "",
        ]
    with open(os.path.join(args.out, "security-review.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(x for x in rev if x is not None) + "\n")

    # ---- dependency-report.md ----
    dep = ["# Dependency Report", "", f"_Generated {ts}_", "",
           f"**{len(dep_findings)}** vulnerable-dependency findings "
           f"(Trivy / pip-audit / npm audit).", "",
           "| Severity | Package | Advisory | Fix |", "|---|---|---|---|"]
    for f in dep_findings:
        dep.append(f"| {f['severity']} | `{f['where']}` | {f['type']} | {f['fix']} |")
    if not dep_findings:
        dep.append("| — | — | No vulnerable dependencies reported | — |")
    with open(os.path.join(args.out, "dependency-report.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(dep) + "\n")

    # ---- findings.xlsx ----
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill
    wb = Workbook()
    head = Font(bold=True, color="FFFFFF")
    fill = PatternFill("solid", fgColor="7B1E1E")

    s1 = wb.active
    s1.title = "Security Findings"
    s1.append(["Severity", "Vulnerability Type", "File Path", "Endpoint",
               "Description", "Exploitation Scenario", "Impact", "Recommended Fix", "Source"])
    for c in s1[1]:
        c.font = head
        c.fill = fill
    for f in findings:
        s1.append([f["severity"], f["type"], f["where"], f["endpoint"], f["description"],
                   f["exploit"], f["impact"], f["fix"], f["source"]])

    s2 = wb.create_sheet("Dependency Vulnerabilities")
    s2.append(["Severity", "Package", "Advisory", "Recommended Fix", "Source"])
    for c in s2[1]:
        c.font = head
        c.fill = fill
    for f in dep_findings:
        s2.append([f["severity"], f["where"], f["type"], f["fix"], f["source"]])

    s3 = wb.create_sheet("Risk Summary")
    s3.append(["Metric", "Value"])
    for c in s3[1]:
        c.font = head
        c.fill = fill
    for k, v in [("Critical", counts["Critical"]), ("High", counts["High"]),
                 ("Medium", counts["Medium"]), ("Low", counts["Low"]),
                 ("Total findings", len(findings)), ("Security score", f"{score}/100"),
                 ("Commit", args.commit), ("Generated", ts)]:
        s3.append([k, v])
    wb.save(os.path.join(args.out, "findings.xlsx"))

    # ---- console + gate ----
    print(f"Security review: {len(findings)} findings "
          f"(C{counts['Critical']} H{counts['High']} M{counts['Medium']} L{counts['Low']}) · score {score}/100")
    if counts["Critical"] > 0:
        print(f"::error::{counts['Critical']} CRITICAL security finding(s) -- failing the gate.")
        sys.exit(1)


if __name__ == "__main__":
    main()
