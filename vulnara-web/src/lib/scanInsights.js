const escapeHtml = (value) => String(value ?? "")
  .replaceAll("&", "&amp;").replaceAll("<", "&lt;")
  .replaceAll(">", "&gt;").replaceAll('"', "&quot;")
  .replaceAll("'", "&#39;");

export function findingKey(finding) {
  return [finding.host, finding.port ?? "", finding.service_name ?? "", finding.cve_id ?? "", finding.cve_id ? "" : finding.ai_reasoning ?? ""]
    .map((value) => String(value).toLowerCase()).join("|");
}

export function compareFindings(current, previous) {
  const currentKeys = new Set(current.map(findingKey));
  const previousKeys = new Set(previous.map(findingKey));
  return {
    newFindings: current.filter((item) => !previousKeys.has(findingKey(item))),
    resolved: previous.filter((item) => !currentKeys.has(findingKey(item))),
    unchanged: current.filter((item) => previousKeys.has(findingKey(item))),
  };
}

export function buildScanReport(scan, findings, logs, remediations) {
  const rows = findings.map((v) => `<tr><td>${escapeHtml(v.severity)}</td><td>${escapeHtml(v.cve_id || "Unmapped")}</td><td>${escapeHtml(v.host)}:${escapeHtml(v.port)}</td><td>${escapeHtml(v.service_name)}</td><td>${escapeHtml(v.service_version)}</td><td>${escapeHtml(v.confidence_score)}</td><td>${escapeHtml(v.status)}</td><td>${escapeHtml(v.ai_reasoning)}</td></tr>`).join("");
  const logRows = logs.map((l) => `<tr><td>${escapeHtml(l.attack_type)}</td><td>${escapeHtml(l.target_url)}</td><td>${escapeHtml(l.target_param)}</td><td>${l.ai_verified ? "Yes" : "No"}</td><td>${escapeHtml(l.risk_rating)}</td><td>${escapeHtml(l.verification_notes)}</td></tr>`).join("");
  const remediationRows = remediations.map((r) => `<tr><td>${escapeHtml(r.vuln_id)}</td><td>${escapeHtml(r.status)}</td><td>${escapeHtml(r.executive_summary)}</td></tr>`).join("");
  return `<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Vulnara scan ${escapeHtml(scan.scan_id)}</title><style>body{font:14px Arial,sans-serif;margin:32px;color:#17212b}h1,h2{color:#0c4566}table{border-collapse:collapse;width:100%;margin:12px 0 28px}th,td{border:1px solid #ccd5dc;padding:8px;text-align:left;vertical-align:top;overflow-wrap:anywhere}th{background:#eaf2f6}p{line-height:1.5}.note{background:#fff4d6;padding:12px}</style></head><body><h1>Vulnara scan report</h1><p><strong>Target:</strong> ${escapeHtml(scan.target)}<br><strong>Scan ID:</strong> ${escapeHtml(scan.scan_id)}<br><strong>Status:</strong> ${escapeHtml(scan.status)}<br><strong>Created:</strong> ${escapeHtml(scan.created_at)}<br><strong>Completed:</strong> ${escapeHtml(scan.completed_at || "Not completed")}</p><p class="note">This report is a snapshot. CVE matches and AI assessments require human review. Active-test results are separate attempts and are not automatically proof of an exploitable vulnerability.</p><h2>Findings (${findings.length})</h2><table><thead><tr><th>Severity</th><th>CVE</th><th>Host:port</th><th>Service</th><th>Version</th><th>AI confidence</th><th>Status</th><th>Reasoning</th></tr></thead><tbody>${rows || '<tr><td colspan="8">No findings recorded.</td></tr>'}</tbody></table><h2>Active-test attempts (${logs.length})</h2><table><thead><tr><th>Type</th><th>URL</th><th>Parameter</th><th>AI verified</th><th>Risk</th><th>Notes</th></tr></thead><tbody>${logRows || '<tr><td colspan="6">No attempts recorded.</td></tr>'}</tbody></table><h2>Remediations (${remediations.length})</h2><table><thead><tr><th>Finding ID</th><th>Status</th><th>Summary</th></tr></thead><tbody>${remediationRows || '<tr><td colspan="3">No remediations recorded.</td></tr>'}</tbody></table></body></html>`;
}

export function downloadScanReport(scan, findings, logs, remediations) {
  const blob = new Blob([buildScanReport(scan, findings, logs, remediations)], { type: "text/html;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `vulnara-scan-${scan.scan_id}.html`;
  anchor.click();
  URL.revokeObjectURL(url);
}
