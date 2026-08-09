import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery, useQueryClient, useMutation } from "@tanstack/react-query";
import { api } from "../lib/api";
import { StatusPill, SeverityBadge, ConfidenceBar, LoadingRow, EmptyState } from "../components/Primitives";
import { VulnTable } from "../components/VulnTable";
import { useScanSocket } from "../hooks/useScanSocket";
import { ConfirmDialog } from "../components/ConfirmDialog";

const TABS = [
  { id: "overview", label: "Overview", icon: "info" },
  { id: "matrix", label: "Threat matrix", icon: "grid_view" },
  { id: "testing", label: "Active testing log", icon: "terminal" },
  { id: "remediation", label: "Remediation", icon: "build_circle" },
];

export function ScanDetailPage() {
  const { scanId } = useParams();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [tab, setTab] = useState("overview");
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
      <div className="p-container-padding">
        <LoadingRow label="Loading scan..." />
      </div>
    );
  }

  const vulns = vulnData?.items ?? [];
  const logs = logsData?.items ?? [];
  const remediations = remData?.items ?? [];
  const counts = scan.vuln_count_by_severity || {};
  const canCancel = ["PENDING", "IN_PROGRESS"].includes(scan.status);
  const progressPct = scan.progress_percent ?? (scan.status === "COMPLETED" ? 100 : scan.status === "IN_PROGRESS" ? 50 : 0);

  return (
    <div className="p-container-padding max-w-[1600px] mx-auto">
      {/* Header Section */}
      <div className="mb-8 flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <div className="flex items-center gap-3 mb-2 flex-wrap">
            <h2 className="font-display-lg text-display-lg font-bold text-on-surface font-code-sm">{scan.target}</h2>
            <StatusPill status={scan.status} />
            {scan.status === "IN_PROGRESS" && (
              <span className="flex items-center gap-1.5 text-xs text-on-surface-variant">
                <span className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse" /> live
              </span>
            )}
          </div>
          <p className="text-on-surface-variant font-body-md text-body-md max-w-2xl">
            Scan <span className="font-code-sm text-primary bg-primary/10 px-1.5 py-0.5 rounded border border-primary/20">{scan.scan_id}</span>{" "}
            &middot; created {new Date(scan.created_at).toLocaleString()}
          </p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={() => navigate("/scans")}
            className="glass-panel px-4 py-2 rounded-md font-body-md text-sm font-medium text-on-surface-variant flex items-center gap-2 hover:bg-surface-variant/50 transition-colors"
          >
            <span className="material-symbols-outlined text-[18px]">arrow_back</span>
            Back to scans
          </button>
          {canCancel && (
            <button
              onClick={() => setCancelOpen(true)}
              className="bg-error/20 border border-error/50 text-error px-4 py-2 rounded-md text-sm font-bold flex items-center gap-2 hover:bg-error/30 transition-colors"
            >
              <span className="material-symbols-outlined text-[18px]">stop_circle</span>
              Cancel scan
            </button>
          )}
        </div>
      </div>

      {/* Recon Status Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="glass-panel p-5 rounded-lg flex flex-col justify-between relative overflow-hidden">
          <div className="absolute top-0 right-0 w-32 h-32 bg-primary/5 rounded-full blur-2xl -mr-10 -mt-10" />
          <div className="flex justify-between items-start mb-4 relative z-10">
            <div className="flex items-center gap-2">
              <span className="material-symbols-outlined text-primary">radar</span>
              <h3 className="font-label-caps text-label-caps text-on-surface-variant uppercase">Scan Status</h3>
            </div>
            <StatusPill status={scan.status} />
          </div>
          <div className="relative z-10">
            <div className="font-headline-md text-xl font-bold text-on-surface">{scan.status.replace(/_/g, " ")}</div>
            <p className="text-sm text-on-surface-variant mt-1">
              {scan.active_testing_enabled ? "Recon, AI triage & active testing." : "Recon + AI triage only."}
            </p>
          </div>
        </div>

        <div className="glass-panel p-5 rounded-lg flex flex-col justify-between">
          <div className="flex justify-between items-start mb-4">
            <div className="flex items-center gap-2">
              <span className="material-symbols-outlined text-on-surface-variant">hourglass_top</span>
              <h3 className="font-label-caps text-label-caps text-on-surface-variant uppercase">Progress</h3>
            </div>
            <span className="font-code-sm font-bold text-primary text-lg">{progressPct}%</span>
          </div>
          <div>
            <div className="w-full bg-[#131313] rounded-full h-2 mb-2 border border-outline-variant/30 overflow-hidden">
              <div className="bg-primary h-2 rounded-full" style={{ width: `${progressPct}%` }} />
            </div>
            <div className="flex justify-between text-xs text-on-surface-variant font-code-sm">
              <span>{scan.started_at ? `Started: ${new Date(scan.started_at).toLocaleTimeString()}` : "Not started"}</span>
              <span>{scan.completed_at ? `Done: ${new Date(scan.completed_at).toLocaleTimeString()}` : "—"}</span>
            </div>
          </div>
        </div>

        <div className="glass-panel p-5 rounded-lg flex flex-col justify-between">
          <div className="flex justify-between items-start mb-2">
            <div className="flex items-center gap-2">
              <span className="material-symbols-outlined text-error">warning</span>
              <h3 className="font-label-caps text-label-caps text-on-surface-variant uppercase">Threats Detected</h3>
            </div>
          </div>
          <div className="flex items-end gap-4 mt-2">
            <div className="flex flex-col">
              <span className="font-display-lg text-4xl font-bold text-critical leading-none">{counts.CRITICAL ?? 0}</span>
              <span className="font-label-caps text-[10px] text-on-surface-variant uppercase mt-1">Critical</span>
            </div>
            <div className="flex flex-col pb-1">
              <span className="font-headline-sm text-xl font-bold text-high leading-none">{counts.HIGH ?? 0}</span>
              <span className="font-label-caps text-[10px] text-on-surface-variant uppercase mt-1">High</span>
            </div>
            <div className="flex flex-col pb-1">
              <span className="font-headline-sm text-xl font-bold text-medium leading-none">{counts.MEDIUM ?? 0}</span>
              <span className="font-label-caps text-[10px] text-on-surface-variant uppercase mt-1">Med</span>
            </div>
            <div className="flex flex-col pb-1">
              <span className="font-headline-sm text-xl font-bold text-low leading-none">{counts.LOW ?? 0}</span>
              <span className="font-label-caps text-[10px] text-on-surface-variant uppercase mt-1">Low</span>
            </div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-1 border-b border-outline-variant mb-6 overflow-x-auto">
        {TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`flex items-center gap-2 px-4 py-3 text-sm font-medium whitespace-nowrap border-b-2 transition-colors ${
              tab === t.id ? "text-primary border-primary" : "text-on-surface-variant border-transparent hover:text-on-surface"
            }`}
          >
            <span className="material-symbols-outlined text-[16px]">{t.icon}</span>
            {t.label}
            {t.id === "testing" && !scan.active_testing_enabled ? " (off)" : ""}
          </button>
        ))}
      </div>

      {tab === "overview" && (
        <div className="glass-panel rounded-xl p-6">
          <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-4 text-sm">
            <dt className="text-on-surface-variant">Target</dt>
            <dd className="font-code-sm text-on-surface">{scan.target}</dd>
            <dt className="text-on-surface-variant">Status</dt>
            <dd><StatusPill status={scan.status} /></dd>
            <dt className="text-on-surface-variant">Active testing</dt>
            <dd className="text-on-surface">{scan.active_testing_enabled ? "Enabled (opt-in)" : "Off"}</dd>
            <dt className="text-on-surface-variant">Authorization</dt>
            <dd className="text-on-surface">{scan.authorization_justification}</dd>
            <dt className="text-on-surface-variant">Started</dt>
            <dd className="text-on-surface">{scan.started_at ? new Date(scan.started_at).toLocaleString() : "Not started yet"}</dd>
            <dt className="text-on-surface-variant">Completed</dt>
            <dd className="text-on-surface">{scan.completed_at ? new Date(scan.completed_at).toLocaleString() : "—"}</dd>
            <dt className="text-on-surface-variant">Socket</dt>
            <dd className="text-xs text-on-surface-variant">{connected ? "connected — receiving live updates" : "disconnected"}</dd>
          </dl>

          {events.length > 0 && (
            <>
              <div className="h-px bg-outline-variant my-6" />
              <div className="font-headline-sm text-sm font-semibold text-on-surface mb-3">Live event stream</div>
              <div className="bg-[#0a0a0a] rounded-lg border border-outline-variant p-4 font-code-sm text-xs text-on-surface-variant max-h-56 overflow-y-auto space-y-1">
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

      {tab === "matrix" && <VulnTable vulnerabilities={vulns} />}

      {tab === "testing" && (
        <div className="glass-panel rounded-xl overflow-hidden">
          {!scan.active_testing_enabled ? (
            <EmptyState
              glyph="block"
              title="Active testing was not enabled for this scan"
              description="This scan ran recon + AI triage only. Re-run with active testing opted in to see SQLi/XSS attempts here."
            />
          ) : logs.length === 0 ? (
            <EmptyState glyph="hourglass_empty" title="No active-test attempts logged yet" description="They'll stream in here as the scan runs." />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse min-w-[800px]">
                <thead className="bg-surface-container-low/50 border-b border-outline-variant">
                  <tr>
                    <th className="p-3 pl-6 font-label-caps text-on-surface-variant uppercase tracking-wider">Type</th>
                    <th className="p-3 font-label-caps text-on-surface-variant uppercase tracking-wider">Target URL</th>
                    <th className="p-3 font-label-caps text-on-surface-variant uppercase tracking-wider">Param</th>
                    <th className="p-3 font-label-caps text-on-surface-variant uppercase tracking-wider">Payload</th>
                    <th className="p-3 font-label-caps text-on-surface-variant uppercase tracking-wider">AI verified</th>
                    <th className="p-3 pr-6 font-label-caps text-on-surface-variant uppercase tracking-wider">Risk</th>
                  </tr>
                </thead>
                <tbody className="font-body-md text-sm">
                  {logs.map((l) => (
                    <tr key={l.log_id} className="border-b border-outline-variant/50">
                      <td className="p-3 pl-6 text-on-surface">{l.attack_type}</td>
                      <td className="p-3 font-code-sm text-on-surface-variant">{l.target_url}</td>
                      <td className="p-3 font-code-sm text-on-surface-variant">{l.target_param || "—"}</td>
                      <td className="p-3 font-code-sm text-on-surface-variant max-w-xs truncate">{l.payload_used}</td>
                      <td className="p-3 text-on-surface-variant">{l.ai_verified ? "✅ Confirmed" : "— Not confirmed"}</td>
                      <td className="p-3 pr-6"><SeverityBadge severity={l.risk_rating} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {tab === "remediation" && (
        <div className="glass-panel rounded-xl overflow-hidden">
          {remediations.length === 0 ? (
            <EmptyState
              glyph="build_circle"
              title="No remediation generated yet"
              description="Open a finding in the threat matrix and click “Generate remediation” to create one."
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse min-w-[800px]">
                <thead className="bg-surface-container-low/50 border-b border-outline-variant">
                  <tr>
                    <th className="p-3 pl-6 font-label-caps text-on-surface-variant uppercase tracking-wider">Vulnerability</th>
                    <th className="p-3 font-label-caps text-on-surface-variant uppercase tracking-wider">Target OS</th>
                    <th className="p-3 font-label-caps text-on-surface-variant uppercase tracking-wider">AI confidence</th>
                    <th className="p-3 pr-6 font-label-caps text-on-surface-variant uppercase tracking-wider">Status</th>
                  </tr>
                </thead>
                <tbody className="font-body-md text-sm">
                  {remediations.map((r) => (
                    <tr
                      key={r.remediation_id}
                      onClick={() => navigate(`/remediations/${r.remediation_id}`)}
                      className="border-b border-outline-variant/50 data-table-row cursor-pointer transition-colors"
                    >
                      <td className="p-3 pl-6 font-code-sm text-primary">{r.vuln_id}</td>
                      <td className="p-3 text-on-surface-variant">{r.target_os || "—"}</td>
                      <td className="p-3"><ConfidenceBar value={r.ai_confidence} /></td>
                      <td className="p-3 pr-6"><StatusPill status={r.status} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

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
