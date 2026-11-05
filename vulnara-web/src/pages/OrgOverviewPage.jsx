import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { api } from "../lib/api";
import { useAuth } from "../context/AuthContext";
import { LoadingRow, EmptyState } from "../components/Primitives";

const SEV_COLOR = {
  CRITICAL: "text-red-400 bg-red-500/10 border-red-500/30",
  HIGH: "text-orange-400 bg-orange-500/10 border-orange-500/30",
  MEDIUM: "text-yellow-400 bg-yellow-500/10 border-yellow-500/30",
  LOW: "text-blue-400 bg-blue-500/10 border-blue-500/30",
  INFO: "text-on-surface-variant bg-surface-variant border-outline-variant",
};

const STATUS_COLOR = {
  COMPLETED: "text-green-400",
  IN_PROGRESS: "text-blue-400",
  PENDING: "text-yellow-400",
  FAILED: "text-red-400",
  CANCELLED: "text-on-surface-variant",
};

function StatCard({ label, value, icon, color }) {
  return (
    <div className="glass-panel rounded-xl p-4 flex items-center gap-3">
      <span className={`material-symbols-outlined text-[26px] ${color}`} style={{ fontVariationSettings: "'FILL' 1" }}>
        {icon}
      </span>
      <div>
        <div className="text-2xl font-bold text-on-surface">{value}</div>
        <div className="text-[11px] text-on-surface-variant uppercase tracking-wider">{label}</div>
      </div>
    </div>
  );
}

export function OrgOverviewPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { data, isLoading } = useQuery({ queryKey: ["overview"], queryFn: () => api.getOverview() });

  if (isLoading) {
    return <div className="p-container-padding"><LoadingRow label="Loading organization overview..." /></div>;
  }

  const m = data?.metrics ?? {};
  const sev = m.findings_by_severity ?? {};
  const assets = data?.assets ?? [];
  const activity = data?.activity ?? [];
  const departments = data?.departments ?? [];
  const isOrg = data?.scope === "organization";

  return (
    <div className="p-container-padding max-w-7xl mx-auto flex flex-col gap-6">
      <div>
        <h2 className="font-display-lg text-display-lg text-on-surface flex items-center gap-3">
          <span className="material-symbols-outlined text-primary text-[32px]">lan</span>
          {isOrg ? "Organization Network Activity" : "Department Network Activity"}
        </h2>
        <p className="text-on-surface-variant mt-2 font-body-md max-w-2xl">
          {isOrg
            ? "Every asset, finding, and scan across the whole organization."
            : "Assets, findings, and scans for your department."}
        </p>
      </div>

      {/* Headline metrics */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard label="Scans" value={m.total_scans ?? 0} icon="radar" color="text-primary" />
        <StatCard label="Assets discovered" value={m.total_assets ?? 0} icon="dns" color="text-blue-400" />
        <StatCard label="Open findings" value={m.open_findings ?? 0} icon="bug_report" color="text-orange-400" />
        <StatCard label="Critical" value={sev.CRITICAL ?? 0} icon="warning" color="text-red-400" />
      </div>

      {/* Severity breakdown */}
      <div className="glass-panel rounded-xl p-5">
        <h3 className="text-sm font-bold text-on-surface uppercase tracking-wider mb-4">Findings by severity</h3>
        <div className="flex flex-wrap gap-3">
          {["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"].map((s) => (
            <div key={s} className={`px-4 py-2 rounded-lg border ${SEV_COLOR[s]} flex items-center gap-2`}>
              <span className="text-lg font-bold">{sev[s] ?? 0}</span>
              <span className="text-[11px] uppercase tracking-wider">{s}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Per-department breakdown (admin only) */}
      {isOrg && departments.length > 0 && (
        <div className="glass-panel rounded-xl p-5">
          <h3 className="text-sm font-bold text-on-surface uppercase tracking-wider mb-4">Scans by department</h3>
          <div className="flex flex-wrap gap-3">
            {departments.map((d) => (
              <div key={d.name} className="px-4 py-2 rounded-lg border border-outline-variant bg-surface-variant flex items-center gap-2">
                <span className="material-symbols-outlined text-[16px] text-primary">groups</span>
                <span className="text-on-surface text-sm font-medium">{d.name}</span>
                <span className="text-on-surface-variant text-xs">{d.scan_count} scans</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Asset inventory */}
        <div className="glass-panel rounded-xl overflow-hidden flex flex-col">
          <div className="p-4 border-b border-outline-variant/40 flex items-center gap-2">
            <span className="material-symbols-outlined text-primary text-[20px]">inventory_2</span>
            <h3 className="text-sm font-bold text-on-surface uppercase tracking-wider">Discovered assets</h3>
          </div>
          {assets.length === 0 ? (
            <EmptyState glyph="dns" title="No assets yet" description="Run a scan to discover hosts and services." />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm min-w-[480px]">
                <thead className="bg-surface-container-low/60 text-[10px] uppercase tracking-wider text-on-surface-variant">
                  <tr>
                    <th className="px-4 py-2.5">Host : Port</th>
                    <th className="px-4 py-2.5">Service</th>
                    <th className="px-4 py-2.5">Findings</th>
                    <th className="px-4 py-2.5">Max CVSS</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-outline-variant/20 font-code-sm">
                  {assets.map((a, i) => (
                    <tr key={i} className="hover:bg-white/[0.02]">
                      <td className="px-4 py-2.5 text-primary">{a.host}:{a.port}</td>
                      <td className="px-4 py-2.5 text-on-surface-variant">{a.service_name || "—"}</td>
                      <td className="px-4 py-2.5 text-on-surface">{a.finding_count}</td>
                      <td className="px-4 py-2.5">
                        <span className={a.max_cvss >= 9 ? "text-red-400" : a.max_cvss >= 7 ? "text-orange-400" : "text-on-surface-variant"}>
                          {a.max_cvss != null ? a.max_cvss.toFixed(1) : "—"}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Activity feed */}
        <div className="glass-panel rounded-xl overflow-hidden flex flex-col">
          <div className="p-4 border-b border-outline-variant/40 flex items-center gap-2">
            <span className="material-symbols-outlined text-primary text-[20px]">timeline</span>
            <h3 className="text-sm font-bold text-on-surface uppercase tracking-wider">Recent activity</h3>
          </div>
          {activity.length === 0 ? (
            <EmptyState glyph="timeline" title="No activity yet" description="Scans will appear here as they run." />
          ) : (
            <div className="divide-y divide-outline-variant/20 max-h-[420px] overflow-y-auto">
              {activity.map((ev) => (
                <button
                  key={ev.scan_id}
                  onClick={() => navigate(`/scans/${ev.scan_id}`)}
                  className="w-full text-left px-4 py-3 hover:bg-white/[0.02] flex items-center justify-between gap-3"
                >
                  <div className="min-w-0">
                    <div className="text-sm text-on-surface truncate font-code-sm">{ev.target}</div>
                    <div className="text-[11px] text-on-surface-variant">
                      {ev.user_full_name || ev.user_email} · {new Date(ev.created_at).toLocaleString()}
                    </div>
                  </div>
                  <div className="flex items-center gap-3 shrink-0">
                    <span className="text-xs text-on-surface-variant">{ev.finding_count} findings</span>
                    <span className={`text-[11px] font-bold uppercase ${STATUS_COLOR[ev.status] || "text-on-surface-variant"}`}>
                      {ev.status}
                    </span>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
