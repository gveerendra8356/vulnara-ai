import {
  mockUser,
  mockUsers,
  mockScans,
  mockVulnerabilities,
  mockThreatLogs,
  mockRemediations,
  mockConfigs,
  mockCveDefs,
  nextId,
} from "./mockData";

// Mutable in-memory copies so create/update calls actually persist for the
// lifetime of the browser tab (resets on refresh — there is no real DB
// behind Mock Mode, by design).
const state = {
  users: [...mockUsers],
  scans: mockScans.map((s) => ({ ...s })),
  vulns: mockVulnerabilities.map((v) => ({ ...v })),
  threatLogs: mockThreatLogs.map((t) => ({ ...t })),
  remediations: mockRemediations.map((r) => ({ ...r })),
  configs: mockConfigs.map((c) => ({ ...c })),
  cveDefs: mockCveDefs.map((c) => ({ ...c })),
  currentUser: null,
};

const delay = (ms = 260) => new Promise((res) => setTimeout(res, ms));

function severityCounts(scanId) {
  const counts = { CRITICAL: 0, HIGH: 0, MEDIUM: 0, LOW: 0, INFO: 0 };
  state.vulns
    .filter((v) => v.scan_id === scanId)
    .forEach((v) => {
      counts[v.severity] = (counts[v.severity] || 0) + 1;
    });
  return counts;
}

function requireAuth() {
  if (!state.currentUser) {
    const err = new Error("Not authenticated");
    err.status = 401;
    throw err;
  }
  return state.currentUser;
}

// ---------------- Auth ----------------

async function login({ email }) {
  await delay();
  const user = state.users.find((u) => u.email === email) || mockUser;
  state.currentUser = user;
  return {
    access_token: `mock.${user.user_id}.token`,
    refresh_token: `mock.${user.user_id}.refresh`,
    token_type: "bearer",
    expires_in: 3600,
    user,
  };
}

async function register({ email, full_name, role }) {
  await delay();
  const user = {
    user_id: nextId("usr"),
    email,
    full_name,
    role: role || "client",
    created_at: new Date().toISOString(),
  };
  state.users.push(user);
  return user;
}

async function me() {
  await delay(120);
  return requireAuth();
}

async function logout() {
  await delay(80);
  state.currentUser = null;
}

// ---------------- Scans ----------------

async function listScans({ status, target } = {}) {
  await delay();
  requireAuth();
  let items = [...state.scans].sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
  if (status) items = items.filter((s) => s.status === status);
  if (target) items = items.filter((s) => s.target.toLowerCase().includes(target.toLowerCase()));
  return { items, total: items.length, page: 1, page_size: items.length };
}

async function createScan(payload) {
  await delay(400);
  const user = requireAuth();
  if (!payload.authorization_confirmed) {
    const err = new Error(
      "Scan cannot be created: authorization_confirmed must be true. Vulnara only scans targets you own or have explicit written permission to test."
    );
    err.status = 422;
    throw err;
  }
  if (!payload.authorization_justification?.trim()) {
    const err = new Error("authorization_justification is required and cannot be blank.");
    err.status = 422;
    throw err;
  }
  const scan = {
    scan_id: nextId("scan"),
    user_id: user.user_id,
    target: payload.target,
    authorization_confirmed: true,
    authorization_justification: payload.authorization_justification,
    active_testing_enabled: !!payload.active_testing_enabled,
    status: "PENDING",
    started_at: null,
    completed_at: null,
    created_at: new Date().toISOString(),
  };
  state.scans.unshift(scan);
  simulateScanLifecycle(scan.scan_id);
  return scan;
}

async function getScan(scanId) {
  await delay(150);
  requireAuth();
  const scan = state.scans.find((s) => s.scan_id === scanId);
  if (!scan) {
    const err = new Error("Scan not found");
    err.status = 404;
    throw err;
  }
  return { ...scan, vuln_count_by_severity: severityCounts(scanId) };
}

async function cancelScan(scanId) {
  await delay(200);
  requireAuth();
  const scan = state.scans.find((s) => s.scan_id === scanId);
  if (!scan) throw new Error("Scan not found");
  if (["COMPLETED", "FAILED", "CANCELLED"].includes(scan.status)) {
    const err = new Error("Scan already finished and cannot be cancelled.");
    err.status = 409;
    throw err;
  }
  scan.status = "CANCELLED";
  return { scan_id: scan.scan_id, status: scan.status };
}

// ---------------- Vulnerabilities ----------------

async function listVulnerabilities(scanId, filters = {}) {
  await delay();
  requireAuth();
  let items = state.vulns.filter((v) => v.scan_id === scanId);
  if (filters.severity?.length) items = items.filter((v) => filters.severity.includes(v.severity));
  if (filters.status) items = items.filter((v) => v.status === filters.status);
  if (filters.min_confidence != null)
    items = items.filter((v) => v.confidence_score >= filters.min_confidence);
  const sortBy = filters.sort_by || "discovered_at";
  const dir = filters.sort_dir === "asc" ? 1 : -1;
  items = [...items].sort((a, b) => (a[sortBy] > b[sortBy] ? 1 : -1) * dir);
  return { items, total: items.length, page: 1, page_size: items.length };
}

async function getVulnerability(vulnId) {
  await delay(150);
  requireAuth();
  const vuln = state.vulns.find((v) => v.vuln_id === vulnId);
  if (!vuln) throw new Error("Vulnerability not found");
  const cve = vuln.cve_id ? state.cveDefs.find((c) => c.cve_id === vuln.cve_id) : null;
  const related_threat_logs = state.threatLogs.filter((t) => t.vuln_id === vulnId);
  return { ...vuln, cve: cve || null, related_threat_logs };
}

async function updateVulnerability(vulnId, { status }) {
  await delay(200);
  requireAuth();
  const vuln = state.vulns.find((v) => v.vuln_id === vulnId);
  if (!vuln) throw new Error("Vulnerability not found");
  vuln.status = status;
  return { ...vuln };
}

// ---------------- Threat logs ----------------

async function listThreatLogs(scanId, filters = {}) {
  await delay();
  requireAuth();
  let items = state.threatLogs.filter((t) => t.scan_id === scanId);
  if (filters.attack_type) items = items.filter((t) => t.attack_type === filters.attack_type);
  if (filters.ai_verified != null) items = items.filter((t) => t.ai_verified === filters.ai_verified);
  return { items, total: items.length, page: 1, page_size: items.length };
}

// ---------------- Remediations ----------------

async function createRemediation(vulnId, { target_os }) {
  await delay(900); // simulate the Gemini generation round-trip
  requireAuth();
  const vuln = state.vulns.find((v) => v.vuln_id === vulnId);
  if (!vuln) throw new Error("Vulnerability not found");
  const rem = {
    remediation_id: nextId("rem"),
    vuln_id: vulnId,
    target_os: target_os || "ubuntu-22.04",
    executive_summary: `A ${vuln.severity.toLowerCase()}-severity issue was found in ${vuln.service_name || "a service"} on ${vuln.host}${
      vuln.port ? `:${vuln.port}` : ""
    }. We recommend applying the vendor patch and re-scanning to confirm the fix. This summary was generated automatically — a reviewer should verify it before it's shared externally.`,
    technical_script: `#!/bin/bash
# Auto-generated remediation draft for ${vuln.cve_id || "finding " + vuln.vuln_id}
# Target OS: ${target_os || "ubuntu-22.04"}
set -euo pipefail

echo "Update and restart the affected service (${vuln.service_name || "service"})..."
apt-get update -y
apt-get install --only-upgrade -y ${(vuln.service_name || "package").toLowerCase().split(" ")[0]}
systemctl restart ${(vuln.service_name || "service").toLowerCase().split(" ")[0]} || true
`,
    ai_confidence: Math.max(0.35, Math.min(0.95, vuln.confidence_score - 0.05)),
    status: "PENDING",
    reviewed_by: null,
    reviewed_at: null,
    executed_at: null,
    created_at: new Date().toISOString(),
  };
  state.remediations.unshift(rem);
  return rem;
}

async function getRemediation(remId) {
  await delay(150);
  requireAuth();
  const rem = state.remediations.find((r) => r.remediation_id === remId);
  if (!rem) throw new Error("Remediation not found");
  return { ...rem };
}

async function listAllRemediations(filters = {}) {
  await delay();
  requireAuth();
  let items = [...state.remediations];
  if (filters.status) items = items.filter((r) => r.status === filters.status);
  items.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
  return { items, total: items.length, page: 1, page_size: items.length };
}

async function listScanRemediations(scanId, filters = {}) {
  await delay();
  requireAuth();
  const vulnIds = state.vulns.filter((v) => v.scan_id === scanId).map((v) => v.vuln_id);
  let items = state.remediations.filter((r) => vulnIds.includes(r.vuln_id));
  if (filters.status) items = items.filter((r) => r.status === filters.status);
  return { items, total: items.length, page: 1, page_size: items.length };
}

async function approveRemediation(remId) {
  await delay(250);
  const user = requireAuth();
  const rem = state.remediations.find((r) => r.remediation_id === remId);
  if (!rem) throw new Error("Remediation not found");
  rem.status = "APPROVED";
  rem.reviewed_by = user.user_id;
  rem.reviewed_at = new Date().toISOString();
  return { ...rem };
}

async function rejectRemediation(remId, reason) {
  await delay(250);
  const user = requireAuth();
  const rem = state.remediations.find((r) => r.remediation_id === remId);
  if (!rem) throw new Error("Remediation not found");
  rem.status = "REJECTED";
  rem.reviewed_by = user.user_id;
  rem.reviewed_at = new Date().toISOString();
  rem.reject_reason = reason;
  return { ...rem };
}

async function markExecuted(remId) {
  await delay(250);
  requireAuth();
  const rem = state.remediations.find((r) => r.remediation_id === remId);
  if (!rem) throw new Error("Remediation not found");
  if (rem.status !== "APPROVED") {
    const err = new Error("Only an APPROVED remediation can be marked executed.");
    err.status = 409;
    throw err;
  }
  rem.status = "EXECUTED";
  rem.executed_at = new Date().toISOString();
  return { ...rem };
}

// ---------------- Admin: config ----------------

async function listConfig() {
  await delay();
  requireAuth();
  return [...state.configs];
}

async function updateConfig(key, value) {
  await delay(200);
  const user = requireAuth();
  const cfg = state.configs.find((c) => c.config_key === key);
  if (!cfg) throw new Error("Config key not found");
  cfg.config_value = value;
  cfg.updated_by = user.user_id;
  cfg.updated_at = new Date().toISOString();
  return { ...cfg };
}

// ---------------- Admin: CVE definitions ----------------

async function listCveDefs(filters = {}) {
  await delay();
  requireAuth();
  let items = [...state.cveDefs];
  if (filters.cve_id) items = items.filter((c) => c.cve_id.toLowerCase().includes(filters.cve_id.toLowerCase()));
  if (filters.severity) items = items.filter((c) => c.severity === filters.severity);
  return { items, total: items.length, page: 1, page_size: items.length };
}

async function syncCveDefs() {
  await delay(700);
  requireAuth();
  return { sync_job_id: nextId("sync"), status: "STARTED" };
}

// ---------------- Simulated live scan + WebSocket ----------------

const socketSubscribers = new Map(); // scan_id -> Set(handler)

function emit(scanId, message) {
  const subs = socketSubscribers.get(scanId);
  if (!subs) return;
  subs.forEach((handler) => handler(message));
}

function connectScanSocket(scanId, onMessage) {
  if (!socketSubscribers.has(scanId)) socketSubscribers.set(scanId, new Set());
  socketSubscribers.get(scanId).add(onMessage);
  return () => {
    socketSubscribers.get(scanId)?.delete(onMessage);
  };
}

async function simulateScanLifecycle(scanId) {
  const scan = state.scans.find((s) => s.scan_id === scanId);
  if (!scan) return;

  await delay(700);
  scan.status = "IN_PROGRESS";
  scan.started_at = new Date().toISOString();
  emit(scanId, { event: "scan.status_changed", scan_id: scanId, timestamp: iso(), data: { status: "IN_PROGRESS" } });

  const stages = [
    { stage: "host_discovery", percent_complete: 25, hosts_found: 1, ports_found: 0 },
    { stage: "port_scan", percent_complete: 55, hosts_found: 1, ports_found: 6 },
    { stage: "banner_grab", percent_complete: 85, hosts_found: 1, ports_found: 6 },
  ];
  for (const s of stages) {
    await delay(650);
    emit(scanId, { event: "recon.progress", scan_id: scanId, timestamp: iso(), data: s });
  }

  await delay(500);
  const newVuln = {
    vuln_id: nextId("vuln"),
    scan_id: scanId,
    cve_id: "CVE-2023-44487",
    host: scan.target,
    port: 443,
    service_name: "nginx",
    service_version: "1.24.0",
    severity: "HIGH",
    cvss_score: 7.5,
    confidence_score: 0.79,
    ai_reasoning:
      "Live-simulated finding for this scan: HTTP/2 enabled on a version predating the Rapid Reset mitigation.",
    status: "OPEN",
    discovered_at: iso(),
  };
  state.vulns.push(newVuln);
  emit(scanId, {
    event: "vulnerability.discovered",
    scan_id: scanId,
    timestamp: iso(),
    data: {
      vuln_id: newVuln.vuln_id,
      severity: newVuln.severity,
      host: newVuln.host,
      port: newVuln.port,
      service_name: newVuln.service_name,
      confidence_score: newVuln.confidence_score,
    },
  });

  await delay(400);
  const critVuln = {
    vuln_id: nextId("vuln"),
    scan_id: scanId,
    cve_id: "CVE-2021-41773",
    host: scan.target,
    port: 8080,
    service_name: "Apache httpd",
    service_version: "2.4.49",
    severity: "CRITICAL",
    cvss_score: 9.8,
    confidence_score: 0.91,
    ai_reasoning: "Live-simulated finding: vulnerable Apache banner on an internal admin path.",
    status: "OPEN",
    discovered_at: iso(),
  };
  state.vulns.push(critVuln);
  emit(scanId, {
    event: "vulnerability.discovered",
    scan_id: scanId,
    timestamp: iso(),
    data: {
      vuln_id: critVuln.vuln_id,
      severity: critVuln.severity,
      host: critVuln.host,
      port: critVuln.port,
      service_name: critVuln.service_name,
      confidence_score: critVuln.confidence_score,
    },
  });
  emit(scanId, {
    event: "alert.critical",
    scan_id: scanId,
    timestamp: iso(),
    data: {
      vuln_id: critVuln.vuln_id,
      host: critVuln.host,
      service_name: critVuln.service_name,
      summary: `Critical: ${critVuln.service_name} on ${critVuln.host}:${critVuln.port} matches ${critVuln.cve_id}`,
    },
  });

  if (scan.active_testing_enabled) {
    await delay(500);
    const log = {
      log_id: nextId("log"),
      scan_id: scanId,
      vuln_id: null,
      attack_type: "XSS",
      target_url: `https://${scan.target}/search`,
      target_param: "q",
      payload_used: "<script>alert(1)</script>",
      ai_verified: true,
      verification_notes: "Live-simulated: payload reflected unescaped in a live script context.",
      risk_rating: "HIGH",
      executed_at: iso(),
    };
    state.threatLogs.push(log);
    emit(scanId, {
      event: "active_test.attempt",
      scan_id: scanId,
      timestamp: iso(),
      data: {
        log_id: log.log_id,
        attack_type: log.attack_type,
        target_url: log.target_url,
        ai_verified: log.ai_verified,
        risk_rating: log.risk_rating,
      },
    });
  }

  await delay(500);
  scan.status = "COMPLETED";
  scan.completed_at = new Date().toISOString();
  emit(scanId, {
    event: "scan.completed",
    scan_id: scanId,
    timestamp: iso(),
    data: { status: "COMPLETED", vuln_count_by_severity: severityCounts(scanId) },
  });
}

function iso() {
  return new Date().toISOString();
}



// ---------------- Profile & Admin User Management (stubs for mock mode) ----------------

async function updateProfile(payload) {
  await delay();
  const user = requireAuth();
  if (payload.full_name) user.full_name = payload.full_name;
  if (payload.email) user.email = payload.email;
  state.currentUser = user;
  return { ...user };
}

async function listUsers() {
  await delay();
  requireAuth();
  return state.users.map((u) => ({
    ...u,
    scan_count: state.scans.filter((s) => s.user_id === u.user_id).length,
  }));
}

async function getUserScans(userId) {
  await delay();
  requireAuth();
  const user = state.users.find((u) => u.user_id === userId);
  if (!user) throw new Error("User not found");
  const scans = state.scans.filter((s) => s.user_id === userId);
  return { user, scans };
}

async function toggleUserActive(userId, isActive) {
  await delay();
  requireAuth();
  const user = state.users.find((u) => u.user_id === userId);
  if (!user) throw new Error("User not found");
  user.is_active = isActive;
  return { ...user };
}

export const mockApi = {
  login,
  register,
  me,
  logout,
  updateProfile,
  listScans,
  createScan,
  getScan,
  cancelScan,
  listVulnerabilities,
  getVulnerability,
  updateVulnerability,
  listThreatLogs,
  createRemediation,
  getRemediation,
  listAllRemediations,
  listScanRemediations,
  approveRemediation,
  rejectRemediation,
  markExecuted,
  listConfig,
  updateConfig,
  listCveDefs,
  syncCveDefs,
  connectScanSocket,
  listUsers,
  getUserScans,
  toggleUserActive,
};

