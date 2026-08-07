// In-memory seed data for Mock Mode. Shapes mirror the Task 2 API contract
// exactly, so swapping VITE_USE_MOCK to "false" later requires no changes
// to any page or component — only to lib/apiClient.js's transport.

let idCounter = 1;
const nextId = (prefix) => `${prefix}-${(idCounter++).toString().padStart(4, "0")}`;

export const mockUser = {
  user_id: "usr-0001",
  email: "analyst@vulnara.dev",
  full_name: "Priya Analyst",
  role: "analyst",
  last_login_at: new Date().toISOString(),
};

export const mockUsers = [
  mockUser,
  {
    user_id: "usr-0002",
    email: "admin@vulnara.dev",
    full_name: "Arjun Admin",
    role: "admin",
    last_login_at: new Date(Date.now() - 3600_000).toISOString(),
  },
];

const now = Date.now();
const hoursAgo = (h) => new Date(now - h * 3600_000).toISOString();

export const mockScans = [
  {
    scan_id: "scan-1001",
    user_id: "usr-0001",
    target: "staging.acmecorp.test",
    authorization_confirmed: true,
    authorization_justification:
      "Written pentest authorization from Acme Corp CTO, ref AUTH-2026-014, valid through 2026-09-30.",
    active_testing_enabled: true,
    status: "COMPLETED",
    started_at: hoursAgo(30),
    completed_at: hoursAgo(29.5),
    created_at: hoursAgo(30.1),
  },
  {
    scan_id: "scan-1002",
    user_id: "usr-0001",
    target: "192.168.56.101",
    authorization_confirmed: true,
    authorization_justification: "Internal lab VM owned by the project author for thesis demonstration.",
    active_testing_enabled: false,
    status: "COMPLETED",
    started_at: hoursAgo(9),
    completed_at: hoursAgo(8.7),
    created_at: hoursAgo(9.1),
  },
  {
    scan_id: "scan-1003",
    user_id: "usr-0001",
    target: "api.acmecorp.test",
    authorization_confirmed: true,
    authorization_justification: "Written pentest authorization from Acme Corp CTO, ref AUTH-2026-014.",
    active_testing_enabled: true,
    status: "IN_PROGRESS",
    started_at: hoursAgo(0.05),
    completed_at: null,
    created_at: hoursAgo(0.06),
  },
  {
    scan_id: "scan-1004",
    user_id: "usr-0001",
    target: "10.0.4.22",
    authorization_confirmed: true,
    authorization_justification: "Client-owned staging box, permission email attached to ticket VUL-88.",
    active_testing_enabled: false,
    status: "FAILED",
    started_at: hoursAgo(60),
    completed_at: hoursAgo(59.9),
    created_at: hoursAgo(60.1),
  },
];

export const mockCveDefs = [
  {
    cve_id: "CVE-2024-27316",
    description: "Apache HTTP Server: HTTP/2 request smuggling via malformed continuation frames.",
    cvss_v3_score: 7.5,
    severity: "HIGH",
    published_date: "2024-04-04T00:00:00Z",
    last_modified_date: "2024-06-01T00:00:00Z",
    source: "NVD",
  },
  {
    cve_id: "CVE-2023-44487",
    description: "HTTP/2 Rapid Reset — stream multiplexing abuse enabling denial of service.",
    cvss_v3_score: 7.5,
    severity: "HIGH",
    published_date: "2023-10-10T00:00:00Z",
    last_modified_date: "2023-11-02T00:00:00Z",
    source: "NVD",
  },
  {
    cve_id: "CVE-2021-41773",
    description: "Apache HTTP Server path traversal and remote code execution in mod_cgi.",
    cvss_v3_score: 9.8,
    severity: "CRITICAL",
    published_date: "2021-10-05T00:00:00Z",
    last_modified_date: "2021-10-08T00:00:00Z",
    source: "NVD",
  },
  {
    cve_id: "CVE-2022-31813",
    description: "mod_remoteip X-Forwarded-For spoofing allowing IP-based access control bypass.",
    cvss_v3_score: 9.1,
    severity: "CRITICAL",
    published_date: "2022-07-13T00:00:00Z",
    last_modified_date: "2022-08-01T00:00:00Z",
    source: "NVD",
  },
  {
    cve_id: "CVE-2020-11984",
    description: "mod_proxy_uwsgi buffer over-read leading to potential remote code execution.",
    cvss_v3_score: 6.4,
    severity: "MEDIUM",
    published_date: "2020-08-07T00:00:00Z",
    last_modified_date: "2020-08-20T00:00:00Z",
    source: "NVD",
  },
];

export const mockVulnerabilities = [
  {
    vuln_id: "vuln-2001",
    scan_id: "scan-1001",
    cve_id: "CVE-2021-41773",
    host: "staging.acmecorp.test",
    port: 443,
    service_name: "Apache httpd",
    service_version: "2.4.49",
    severity: "CRITICAL",
    cvss_score: 9.8,
    confidence_score: 0.94,
    ai_reasoning:
      "Detected Apache 2.4.49 banner exactly matches the vulnerable version range for CVE-2021-41773. The /cgi-bin/ path is exposed and mod_cgi appears enabled from the response headers, which are the specific preconditions for exploitation. High confidence this is a genuine, not theoretical, exposure.",
    status: "OPEN",
    discovered_at: hoursAgo(29.6),
  },
  {
    vuln_id: "vuln-2002",
    scan_id: "scan-1001",
    cve_id: "CVE-2024-27316",
    host: "staging.acmecorp.test",
    port: 443,
    service_name: "Apache httpd",
    service_version: "2.4.49",
    severity: "HIGH",
    cvss_score: 7.5,
    confidence_score: 0.81,
    ai_reasoning:
      "Version matches CVE-2024-27316's affected range. HTTP/2 is advertised via ALPN. Confidence is not higher because we could not confirm the continuation-frame handling behavior without active testing enabled for this scan.",
    status: "OPEN",
    discovered_at: hoursAgo(29.6),
  },
  {
    vuln_id: "vuln-2003",
    scan_id: "scan-1001",
    cve_id: null,
    host: "staging.acmecorp.test",
    port: 22,
    service_name: "OpenSSH",
    service_version: "8.9p1",
    severity: "LOW",
    cvss_score: 3.1,
    confidence_score: 0.42,
    ai_reasoning:
      "OpenSSH 8.9p1 has no directly matching high-confidence CVE in the current NVD cache; flagged only because it's a slightly dated build relative to the current stable branch. Likely a false positive — recommend manual review rather than remediation spend.",
    status: "OPEN",
    discovered_at: hoursAgo(29.6),
  },
  {
    vuln_id: "vuln-2004",
    scan_id: "scan-1002",
    cve_id: "CVE-2020-11984",
    host: "192.168.56.101",
    port: 8080,
    service_name: "uWSGI",
    service_version: "2.0.19",
    severity: "MEDIUM",
    cvss_score: 6.4,
    confidence_score: 0.68,
    ai_reasoning:
      "Banner reports uWSGI 2.0.19 which falls inside the affected range for CVE-2020-11984 when fronted by mod_proxy_uwsgi. Could not confirm the Apache-side proxy config from banner data alone, hence moderate rather than high confidence.",
    status: "ACCEPTED_RISK",
    discovered_at: hoursAgo(8.8),
  },
  {
    vuln_id: "vuln-2005",
    scan_id: "scan-1002",
    cve_id: null,
    host: "192.168.56.101",
    port: 3306,
    service_name: "MySQL",
    service_version: "8.0.34",
    severity: "INFO",
    cvss_score: 0.0,
    confidence_score: 0.2,
    ai_reasoning:
      "MySQL is exposed on a non-loopback interface. Current version has no unpatched CVEs in cache; flagged purely as a configuration/exposure note, not a vulnerability.",
    status: "FALSE_POSITIVE",
    discovered_at: hoursAgo(8.8),
  },
  {
    vuln_id: "vuln-2006",
    scan_id: "scan-1003",
    cve_id: "CVE-2023-44487",
    host: "api.acmecorp.test",
    port: 443,
    service_name: "nginx",
    service_version: "1.24.0",
    severity: "HIGH",
    cvss_score: 7.5,
    confidence_score: 0.77,
    ai_reasoning:
      "HTTP/2 is enabled and the version predates the vendor's Rapid Reset mitigation backport. Triage in progress — this scan is still running active tests.",
    status: "OPEN",
    discovered_at: hoursAgo(0.03),
  },
];

export const mockThreatLogs = [
  {
    log_id: "log-3001",
    scan_id: "scan-1001",
    vuln_id: "vuln-2001",
    attack_type: "SQLI",
    target_url: "https://staging.acmecorp.test/login",
    target_param: "username",
    payload_used: "' OR '1'='1",
    ai_verified: false,
    verification_notes: "Payload reflected in error output but no query-structure change detected. Not exploitable.",
    risk_rating: "LOW",
    executed_at: hoursAgo(29.55),
  },
  {
    log_id: "log-3002",
    scan_id: "scan-1001",
    vuln_id: null,
    attack_type: "XSS",
    target_url: "https://staging.acmecorp.test/search",
    target_param: "q",
    payload_used: "<script>alert(1)</script>",
    ai_verified: true,
    verification_notes:
      "Payload was reflected unescaped in the response body inside a live <script> context and would execute in a browser. Confirmed reflected XSS, not just string presence.",
    risk_rating: "HIGH",
    executed_at: hoursAgo(29.5),
  },
  {
    log_id: "log-3003",
    scan_id: "scan-1003",
    vuln_id: null,
    attack_type: "SQLI",
    target_url: "https://api.acmecorp.test/v1/users",
    target_param: "id",
    payload_used: "1 AND SLEEP(0)",
    ai_verified: false,
    verification_notes: "Timing-based probe inconclusive so far — scan still in progress.",
    risk_rating: "INFO",
    executed_at: hoursAgo(0.02),
  },
];

export const mockRemediations = [
  {
    remediation_id: "rem-4001",
    vuln_id: "vuln-2001",
    target_os: "ubuntu-20.04",
    executive_summary:
      "The web server on staging.acmecorp.test is running an Apache version with a publicly known path-traversal and remote-code-execution flaw. An attacker could read arbitrary files or run commands on the server. We recommend upgrading Apache immediately and restricting the affected CGI path in the meantime.",
    technical_script: `#!/bin/bash
# Remediation for CVE-2021-41773 — Apache path traversal / RCE
# Target OS: ubuntu-20.04
set -euo pipefail

echo "[1/3] Disabling mod_cgi as an immediate mitigation..."
a2dismod cgi || true

echo "[2/3] Updating package index and upgrading apache2..."
apt-get update -y
apt-get install --only-upgrade -y apache2

echo "[3/3] Restarting apache2..."
systemctl restart apache2

echo "Done. Verify version with: apache2 -v"
`,
    ai_confidence: 0.88,
    status: "PENDING",
    reviewed_by: null,
    reviewed_at: null,
    executed_at: null,
    created_at: hoursAgo(2),
  },
  {
    remediation_id: "rem-4002",
    vuln_id: "vuln-2002",
    target_os: "ubuntu-20.04",
    executive_summary:
      "The web server advertises HTTP/2 on a version predating the vendor's fix for a request-smuggling issue. We recommend patching Apache to the latest 2.4.x release, which includes the fix.",
    technical_script: `#!/bin/bash
# Remediation for CVE-2024-27316 — HTTP/2 continuation frame smuggling
set -euo pipefail
apt-get update -y
apt-get install --only-upgrade -y apache2
systemctl restart apache2
`,
    ai_confidence: 0.74,
    status: "APPROVED",
    reviewed_by: "usr-0002",
    reviewed_at: hoursAgo(1),
    executed_at: null,
    created_at: hoursAgo(3),
  },
  {
    remediation_id: "rem-4003",
    vuln_id: "vuln-2006",
    target_os: "debian-12",
    executive_summary:
      "The API server's nginx build predates the fix for the HTTP/2 Rapid Reset denial-of-service technique. We recommend upgrading nginx to a patched release and enabling stricter per-connection stream limits.",
    technical_script: `#!/bin/bash
# Remediation for CVE-2023-44487 — HTTP/2 Rapid Reset
set -euo pipefail
apt-get update -y
apt-get install --only-upgrade -y nginx
sed -i 's/http2_max_concurrent_streams .*/http2_max_concurrent_streams 64;/' /etc/nginx/nginx.conf || true
systemctl restart nginx
`,
    ai_confidence: 0.7,
    status: "PENDING",
    reviewed_by: null,
    reviewed_at: null,
    executed_at: null,
    created_at: hoursAgo(0.01),
  },
];

export const mockConfigs = [
  {
    config_id: "cfg-5001",
    config_key: "ai_confidence_threshold",
    config_value: "0.4",
    description: "Minimum AI confidence score for a finding to appear in the threat matrix by default.",
    updated_by: "usr-0002",
    updated_at: hoursAgo(200),
  },
  {
    config_id: "cfg-5002",
    config_key: "active_testing_max_requests_per_min",
    config_value: "20",
    description: "Rate limit applied to the active payload testing module per target.",
    updated_by: "usr-0002",
    updated_at: hoursAgo(150),
  },
  {
    config_id: "cfg-5003",
    config_key: "nvd_sync_interval_hours",
    config_value: "12",
    description: "How often the scheduled background job syncs CVE_Definitions from the NVD API.",
    updated_by: "usr-0002",
    updated_at: hoursAgo(400),
  },
];

export { nextId };
