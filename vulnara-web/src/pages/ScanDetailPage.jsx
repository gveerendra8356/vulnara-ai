import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery, useQueryClient, useMutation } from "@tanstack/react-query";
import { api } from "../lib/api";
import { StatusPill, SeverityBadge, LoadingRow, EmptyState } from "../components/Primitives";
import { VulnTable } from "../components/VulnTable";
import { useScanSocket } from "../hooks/useScanSocket";
import { ConfirmDialog } from "../components/ConfirmDialog";

const TABS = ["Overview", "Threat matrix", "Active testing log", "Remediation"];

export function ScanDetailPage() {
  const { scanId } = useParams();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [tab, setTab] = useState("Overview");
  const [cancelOpen, setCancelOpen] = useState(false);

  const { data: scan, isLoading } = useQuery({
    queryKey: ["scan", scanId],
    queryFn: () => api.getScan(scanId),
    refetchInterval: (query) => (["IN_PROGRESS", "PENDING"].includes(query.state.data?.status) ? 4000 : false),
  });

  const { data: vulnData } = useQuery({
    queryKey: ["scan-vulns", scanId],
    queryFn: () => api.listVulnerabilities(scanId),
    enabled: !!scan,
  });

  const { data: logsData } = useQuery({
    queryKey: ["scan-threat-logs", scanId],
    queryFn: () => api.listThreatLogs(scanId),
    enabled: !!scan && scan.active_testing_enabled,
  });

  const { data: remData } = useQuery({
    queryKey: ["scan-remediations", scanId],
    queryFn: () => api.listScanRemediations(scanId),
    enabled: !!scan,
  });

  const { events, connected } = useScanSocket(scanId, {
    onEvent: (msg) => {
      if (["scan.status_changed", "scan.completed", "scan.failed"].includes(msg.event)) {
        qc.invalidateQueries({ queryKey: ["scan", scanId] });
      }
      if (["vulnerability.discovered", "scan.completed"].includes(msg.event)) {
        qc.invalidateQueries({ queryKey: ["scan-vulns", scanId] });
      }
      if (msg.event === "active_test.attempt") {
        qc.invalidateQueries({ queryKey: ["scan-threat-logs", scanId] });
      }
    },
  });

  const cancelMutation = useMutation({
    mutationFn: () => api.cancelScan(scanId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["scan", scanId] });
      setCancelOpen(false);
    },
  });

  if (isLoading || !scan) {
    return (
      <div className="page">
        <LoadingRow label="Loading scan..." />
      </div>
    );
  }

  const vulns = vulnData?.items ?? [];
  const logs = logsData?.items ?? [];
  const remediations = remData?.items ?? [];
  const counts = scan.vuln_count_by_severity || {};
  const canCancel = ["PENDING", "IN_PROGRESS"].includes(scan.status);

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}>
            <h1 className="page-title mono" style={{ margin: 0 }}>
              {scan.target}
            </h1>
            <StatusPill status={scan.status} />
            {scan.status === "IN_PROGRESS" && (
              <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
                <span className="pulse-dot" />
                <span className="small-note">live</span>
              </span>
            )}
          </div>
          <p className="page-subtitle">
            Scan <span className="mono">{scan.scan_id}</span> · created {new Date(scan.created_at).toLocaleString()}
          </p>
        </div>
        <div style={{ display: "flex", gap: 10 }}>
          {canCancel && (
            <button className="btn btn-danger" onClick={() => setCancelOpen(true)}>
              Cancel scan
            </button>
          )}
          <button className="btn btn-ghost" onClick={() => navigate("/scans")}>
            ← Back to scans
          </button>
        </div>
      </div>

      <div className="grid grid-4" style={{ marginBottom: 16 }}>
        {["CRITICAL", "HIGH", "MEDIUM", "LOW"].map((sev) => (
          <div key={sev} className="panel stat-card">
            <div className="stat-label">{sev}</div>
            <div className={`stat-value ${sev.toLowerCase()}`}>{counts[sev] ?? 0}</div>
          </div>
        ))}
      </div>

      <div className="panel" style={{ marginBottom: 20 }}>
        <div className="tabs">
          {TABS.map((t) => (
            <button key={t} className={`tab-btn${tab === t ? " active" : ""}`} onClick={() => setTab(t)}>
              {t}
              {t === "Active testing log" && !scan.active_testing_enabled ? " (off)" : ""}
            </button>
          ))}
        </div>

        {tab === "Overview" && (
          <div className="panel-pad">
            <dl className="kv-grid">
              <dt>Target</dt>
              <dd className="mono">{scan.target}</dd>
              <dt>Status</dt>
              <dd>
                <StatusPill status={scan.status} />
              </dd>
              <dt>Active testing</dt>
              <dd>{scan.active_testing_enabled ? "Enabled (opt-in)" : "Off"}</dd>
              <dt>Authorization</dt>
              <dd>{scan.authorization_justification}</dd>
              <dt>Started</dt>
              <dd>{scan.started_at ? new Date(scan.started_at).toLocaleString() : "Not started yet"}</dd>
              <dt>Completed</dt>
              <dd>{scan.completed_at ? new Date(scan.completed_at).toLocaleString() : "—"}</dd>
              <dt>Socket</dt>
              <dd className="small-note">{connected ? "connected — receiving live updates" : "disconnected"}</dd>
            </dl>

            {events.length > 0 && (
              <>
                <div className="divider" />
                <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>Live event stream</div>
                <div className="code-block" style={{ maxHeight: 220, overflowY: "auto" }}>
                  {events
                    .slice()
                    .reverse()
                    .map((e, i) => (
                      <div key={i}>
                        [{new Date(e.timestamp).toLocaleTimeString()}] {e.event} {JSON.stringify(e.data)}
                      </div>
                    ))}
                </div>
              </>
            )}
          </div>
        )}

        {tab === "Threat matrix" && <div style={{ padding: 20 }}><VulnTable vulnerabilities={vulns} /></div>}

        {tab === "Active testing log" && (
          <div className="panel-pad">
            {!scan.active_testing_enabled ? (
              <EmptyState
                glyph="⊘"
                title="Active testing was not enabled for this scan"
                description="This scan ran recon + AI triage only. Re-run with active testing opted in to see SQLi/XSS attempts here."
              />
            ) : logs.length === 0 ? (
              <EmptyState glyph="…" title="No active-test attempts logged yet" description="They'll stream in here as the scan runs." />
            ) : (
              <div className="scroll-x">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Type</th>
                      <th>Target URL</th>
                      <th>Param</th>
                      <th>Payload</th>
                      <th>AI verified</th>
                      <th>Risk</th>
                    </tr>
                  </thead>
                  <tbody>
                    {logs.map((l) => (
                      <tr key={l.log_id} style={{ cursor: "default" }}>
                        <td>{l.attack_type}</td>
                        <td className="mono">{l.target_url}</td>
                        <td className="mono">{l.target_param || "—"}</td>
                        <td className="mono">{l.payload_used}</td>
                        <td>{l.ai_verified ? "✅ Confirmed" : "— Not confirmed"}</td>
                        <td>
                          <SeverityBadge severity={l.risk_rating} />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {tab === "Remediation" && (
          <div className="panel-pad">
            {remediations.length === 0 ? (
              <EmptyState
                glyph="✓"
                title="No remediation generated yet"
                description="Open a finding in the threat matrix and click “Generate remediation” to create one."
              />
            ) : (
              <div className="scroll-x">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Vulnerability</th>
                      <th>Target OS</th>
                      <th>AI confidence</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {remediations.map((r) => (
                      <tr key={r.remediation_id} onClick={() => navigate(`/remediations/${r.remediation_id}`)}>
                        <td className="mono">{r.vuln_id}</td>
                        <td>{r.target_os || "—"}</td>
                        <td className="mono">{Math.round(r.ai_confidence * 100)}%</td>
                        <td>
                          <StatusPill status={r.status} />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </div>

      <ConfirmDialog
        open={cancelOpen}
        title="Cancel this scan?"
        body="Recon or triage still in progress will stop. Findings already discovered will remain in the threat matrix."
        confirmLabel={cancelMutation.isPending ? "Cancelling..." : "Cancel scan"}
        danger
        onConfirm={() => cancelMutation.mutate()}
        onCancel={() => setCancelOpen(false)}
        confirmDisabled={cancelMutation.isPending}
      />
    </div>
  );
}
