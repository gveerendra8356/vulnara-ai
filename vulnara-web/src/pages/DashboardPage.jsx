import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, BarChart, Bar, XAxis, YAxis, CartesianGrid } from "recharts";
import { api } from "../lib/api";
import { StatusPill, LoadingRow, EmptyState } from "../components/Primitives";

const SEVERITY_COLORS = {
  CRITICAL: "#dc2626",
  HIGH: "#ea580c",
  MEDIUM: "#eab308",
  LOW: "#3b82f6",
  INFO: "#94a3b8",
};

export function DashboardPage() {
  const navigate = useNavigate();

  const { data: scansData, isLoading: scansLoading } = useQuery({
    queryKey: ["scans", "recent"],
    queryFn: () => api.listScans(),
  });

  const scans = scansData?.items ?? [];

  const { data: allVulns } = useQuery({
    queryKey: ["dashboard-vulns", scans.map((s) => s.scan_id).join(",")],
    queryFn: async () => {
      const results = await Promise.all(scans.map((s) => api.listVulnerabilities(s.scan_id)));
      return results.flatMap((r) => r.items);
    },
    enabled: scans.length > 0,
  });

  const { data: pendingRemediations } = useQuery({
    queryKey: ["dashboard-remediations"],
    queryFn: () => api.listAllRemediations({ status: "PENDING" }),
  });

  const severityCounts = { CRITICAL: 0, HIGH: 0, MEDIUM: 0, LOW: 0, INFO: 0 };
  (allVulns ?? []).forEach((v) => {
    severityCounts[v.severity] = (severityCounts[v.severity] || 0) + 1;
  });
  const pieData = Object.entries(severityCounts)
    .filter(([, v]) => v > 0)
    .map(([name, value]) => ({ name, value }));

  const trendData = [...scans]
    .filter((s) => s.status === "COMPLETED")
    .sort((a, b) => new Date(a.created_at) - new Date(b.created_at))
    .slice(-6)
    .map((s) => ({
      name: s.target.length > 14 ? s.target.slice(0, 14) + "…" : s.target,
      findings: (allVulns ?? []).filter((v) => v.scan_id === s.scan_id).length,
    }));

  const inProgressCount = scans.filter((s) => s.status === "IN_PROGRESS").length;
  const criticalOpen = (allVulns ?? []).filter((v) => v.severity === "CRITICAL" && v.status === "OPEN").length;
  const pendingCount = pendingRemediations?.items?.length ?? 0;

  return (
    <div className="p-container-padding grid grid-cols-12 gap-gutter content-start max-w-[1600px] mx-auto">
      {/* Page Header */}
      <div className="col-span-12 mb-2 flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <h2 className="font-headline-md text-headline-md font-semibold text-on-surface">Global Analytics Overview</h2>
          <p className="text-on-surface-variant mt-1 max-w-2xl">
            Live overview of scan activity, the AI-prioritized threat landscape, and remediation work waiting on
            human review.
          </p>
        </div>
        <button
          onClick={() => navigate("/scans/new")}
          className="bg-primary text-on-primary px-4 py-2 rounded-md flex items-center gap-2 font-bold hover:bg-primary/90 transition-colors shadow-[0_0_15px_rgba(200,198,197,0.3)] self-start"
        >
          <span className="material-symbols-outlined text-[18px]">add</span>
          New Scan
        </button>
      </div>

      {/* KPI Cards Row */}
      <div className="col-span-12 grid grid-cols-1 md:grid-cols-4 gap-gutter">
        <div className="glass-panel rounded-lg p-5 flex flex-col justify-between">
          <div className="flex justify-between items-start mb-4">
            <span className="text-on-surface-variant text-sm font-medium">Total Scans</span>
            <span className="material-symbols-outlined text-primary text-[20px]">radar</span>
          </div>
          <span className="font-display-lg text-[32px] leading-tight font-bold text-on-surface">{scans.length}</span>
        </div>
        <div className="glass-panel rounded-lg p-5 flex flex-col justify-between">
          <div className="flex justify-between items-start mb-4">
            <span className="text-on-surface-variant text-sm font-medium">Scans In Progress</span>
            <span className="material-symbols-outlined text-primary text-[20px]">sync</span>
          </div>
          <span className="font-display-lg text-[32px] leading-tight font-bold text-on-surface">{inProgressCount}</span>
        </div>
        <div className="glass-panel rounded-lg p-5 flex flex-col justify-between border border-error/30 shadow-[0_0_15px_rgba(220,38,38,0.15)]">
          <div className="flex justify-between items-start mb-4">
            <span className="text-error text-sm font-medium">Open Critical Findings</span>
            <span className="material-symbols-outlined text-error text-[20px]" style={{ fontVariationSettings: "'FILL' 1" }}>
              warning
            </span>
          </div>
          <span className="font-display-lg text-[32px] leading-tight font-bold text-error">{criticalOpen}</span>
        </div>
        <div className="glass-panel rounded-lg p-5 flex flex-col justify-between border-t-2 border-medium">
          <div className="flex justify-between items-start mb-4">
            <span className="text-medium text-sm font-medium">Remediations Pending</span>
            <span className="material-symbols-outlined text-medium text-[20px]">build_circle</span>
          </div>
          <span className="font-display-lg text-[32px] leading-tight font-bold text-on-surface">{pendingCount}</span>
        </div>
      </div>

      {/* Charts */}
      <div className="col-span-12 grid grid-cols-1 lg:grid-cols-2 gap-gutter mt-2">
        <div className="glass-panel rounded-lg p-6 flex flex-col">
          <div className="flex justify-between items-center mb-4 border-b border-outline-variant/30 pb-4">
            <h3 className="font-headline-sm text-headline-sm text-on-surface">Findings by severity</h3>
            <span className="text-xs text-on-surface-variant">across all scans</span>
          </div>
          <div style={{ height: 220 }}>
            {pieData.length === 0 ? (
              <EmptyState glyph="donut_large" title="No findings yet" description="Run a scan to populate the threat matrix." />
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={pieData} dataKey="value" nameKey="name" innerRadius={50} outerRadius={78} paddingAngle={3}>
                    {pieData.map((entry) => (
                      <Cell key={entry.name} fill={SEVERITY_COLORS[entry.name]} stroke="none" />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={{ background: "#122131", border: "1px solid #444748", borderRadius: 8, fontSize: 12 }} />
                </PieChart>
              </ResponsiveContainer>
            )}
          </div>
          {pieData.length > 0 && (
            <div className="flex gap-4 flex-wrap pt-3">
              {pieData.map((entry) => (
                <div key={entry.name} className="flex items-center gap-2 text-xs">
                  <span className="w-2 h-2 rounded-full" style={{ background: SEVERITY_COLORS[entry.name] }} />
                  <span className="font-code-sm text-on-surface">{entry.name}</span>
                  <span className="text-on-surface-variant">{entry.value}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="glass-panel rounded-lg p-6 flex flex-col">
          <div className="flex justify-between items-center mb-4 border-b border-outline-variant/30 pb-4">
            <h3 className="font-headline-sm text-headline-sm text-on-surface">Findings per scan (trend)</h3>
            <span className="text-xs text-on-surface-variant">last 6 completed</span>
          </div>
          <div style={{ height: 220 }}>
            {trendData.length === 0 ? (
              <EmptyState glyph="show_chart" title="Not enough history yet" description="Complete a few scans to see a trend." />
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={trendData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#273647" vertical={false} />
                  <XAxis dataKey="name" tick={{ fontSize: 10, fill: "#c4c7c7" }} axisLine={{ stroke: "#444748" }} />
                  <YAxis tick={{ fontSize: 10, fill: "#c4c7c7" }} axisLine={{ stroke: "#444748" }} allowDecimals={false} />
                  <Tooltip contentStyle={{ background: "#122131", border: "1px solid #444748", borderRadius: 8, fontSize: 12 }} />
                  <Bar dataKey="findings" fill="#c8c6c5" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>
      </div>

      {/* Recent Scans */}
      <div className="col-span-12 glass-panel rounded-lg overflow-hidden mt-2">
        <div className="px-6 py-4 border-b border-outline-variant/30 flex justify-between items-center bg-surface-container-low/50">
          <h3 className="font-headline-sm text-headline-sm text-on-surface">Recent Scans</h3>
          <button onClick={() => navigate("/scans")} className="text-primary text-sm hover:underline">
            View All
          </button>
        </div>
        {scansLoading ? (
          <LoadingRow label="Loading scans..." />
        ) : scans.length === 0 ? (
          <EmptyState glyph="biotech" title="No scans yet" description="Submit your first authorized target to get started." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left font-body-md text-sm">
              <thead className="text-on-surface-variant font-semibold uppercase tracking-wider text-[10px] bg-surface-container-low/30">
                <tr>
                  <th className="p-table-cell-padding font-medium border-b border-outline-variant/30">Target</th>
                  <th className="p-table-cell-padding font-medium border-b border-outline-variant/30">Status</th>
                  <th className="p-table-cell-padding font-medium border-b border-outline-variant/30">Active testing</th>
                  <th className="p-table-cell-padding font-medium border-b border-outline-variant/30">Created</th>
                </tr>
              </thead>
              <tbody className="text-on-surface font-code-sm">
                {scans.slice(0, 6).map((s) => (
                  <tr
                    key={s.scan_id}
                    onClick={() => navigate(`/scans/${s.scan_id}`)}
                    className="hover:bg-white/[0.02] transition-colors border-b border-outline-variant/10 cursor-pointer"
                  >
                    <td className="p-table-cell-padding text-primary">{s.target}</td>
                    <td className="p-table-cell-padding">
                      <StatusPill status={s.status} />
                    </td>
                    <td className="p-table-cell-padding text-on-surface-variant">{s.active_testing_enabled ? "Enabled" : "Off"}</td>
                    <td className="p-table-cell-padding text-on-surface-variant text-xs">{new Date(s.created_at).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
