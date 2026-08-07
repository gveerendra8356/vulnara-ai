import { http, TOKEN_KEY, WS_BASE_URL } from "./httpClient";

// Mirrors mockApi.js function-for-function so lib/api.js can switch
// between the two transports with zero changes to any page/component.

async function login({ email, password }) {
  const { data } = await http.post("/auth/login", { email, password });
  localStorage.setItem(TOKEN_KEY, data.access_token);
  if (data.refresh_token) localStorage.setItem("vulnara_refresh_token", data.refresh_token);
  return data;
}

async function register({ email, password, full_name, role }) {
  const { data } = await http.post("/auth/register", { email, password, full_name, role });
  return data;
}

async function me() {
  const { data } = await http.get("/auth/me");
  return data;
}

async function logout() {
  const refresh_token = localStorage.getItem("vulnara_refresh_token");
  try {
    if (refresh_token) await http.post("/auth/logout", { refresh_token });
  } finally {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem("vulnara_refresh_token");
  }
}

async function listScans(params = {}) {
  const { data } = await http.get("/scans", { params });
  return data;
}

async function createScan(payload) {
  const { data } = await http.post("/scans", payload);
  return data;
}

async function getScan(scanId) {
  const { data } = await http.get(`/scans/${scanId}`);
  return data;
}

async function cancelScan(scanId) {
  const { data } = await http.post(`/scans/${scanId}/cancel`);
  return data;
}

async function listVulnerabilities(scanId, filters = {}) {
  const params = { ...filters };
  if (Array.isArray(params.severity)) params.severity = params.severity.join(",");
  const { data } = await http.get(`/scans/${scanId}/vulnerabilities`, { params });
  return data;
}

async function getVulnerability(vulnId) {
  const { data } = await http.get(`/vulnerabilities/${vulnId}`);
  return data;
}

async function updateVulnerability(vulnId, payload) {
  const { data } = await http.patch(`/vulnerabilities/${vulnId}`, payload);
  return data;
}

async function listThreatLogs(scanId, filters = {}) {
  const { data } = await http.get(`/scans/${scanId}/threat-logs`, { params: filters });
  return data;
}

async function createRemediation(vulnId, payload) {
  const { data } = await http.post(`/vulnerabilities/${vulnId}/remediations`, payload);
  return data;
}

async function getRemediation(remId) {
  const { data } = await http.get(`/remediations/${remId}`);
  return data;
}

// Not in the original API contract as a global endpoint (contract only
// defines per-scan listing at 5.3) — used for the cross-scan remediation
// queue page. Falls back to fetching per-scan if your backend doesn't
// expose this; adjust to match whatever you implement.
async function listAllRemediations(filters = {}) {
  const { data } = await http.get("/remediations", { params: filters });
  return data;
}

async function listScanRemediations(scanId, filters = {}) {
  const { data } = await http.get(`/scans/${scanId}/remediations`, { params: filters });
  return data;
}

async function approveRemediation(remId) {
  const { data } = await http.post(`/remediations/${remId}/approve`);
  return data;
}

async function rejectRemediation(remId, reason) {
  const { data } = await http.post(`/remediations/${remId}/reject`, { reason });
  return data;
}

async function markExecuted(remId) {
  const { data } = await http.post(`/remediations/${remId}/mark-executed`);
  return data;
}

async function listConfig() {
  const { data } = await http.get("/admin/config");
  return data;
}

async function updateConfig(key, value) {
  const { data } = await http.patch(`/admin/config/${key}`, { config_value: value });
  return data;
}

async function listCveDefs(filters = {}) {
  const { data } = await http.get("/admin/cve-definitions", { params: filters });
  return data;
}

async function syncCveDefs() {
  const { data } = await http.post("/admin/cve-definitions/sync", {});
  return data;
}

// Real WebSocket connection per API contract section 7.
// Returns an unsubscribe function, matching mockApi's connectScanSocket signature.
function connectScanSocket(scanId, onMessage) {
  const token = localStorage.getItem(TOKEN_KEY) || "";
  const socket = new WebSocket(`${WS_BASE_URL}/ws/scans/${scanId}?token=${encodeURIComponent(token)}`);

  socket.onmessage = (evt) => {
    try {
      const parsed = JSON.parse(evt.data);
      if (parsed.event === "pong") return;
      onMessage(parsed);
    } catch {
      // ignore malformed frames
    }
  };

  const heartbeat = setInterval(() => {
    if (socket.readyState === WebSocket.OPEN) socket.send(JSON.stringify({ event: "ping" }));
  }, 20000);

  return () => {
    clearInterval(heartbeat);
    socket.close();
  };
}

export const realApi = {
  login,
  register,
  me,
  logout,
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
};
