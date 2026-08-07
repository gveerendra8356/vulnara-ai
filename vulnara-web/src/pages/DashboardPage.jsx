import { useQuery } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router-dom";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, BarChart, Bar, XAxis, YAxis, CartesianGrid } from "recharts";
import { api } from "../lib/api";
import { StatusPill, LoadingRow, EmptyState } from "../components/Primitives";

const SEVERITY_COLORS = {
  CRITICAL: "#f24b6b",
  HIGH: "#ff8a4c",
  MEDIUM: "#f2c14e",
  LOW: "#5b93f2",
  INFO: "#7e8ba0",
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

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1 className="page-title">Dashboard</h1>
          <p className="page-subtitle">
            Live overview of your scan activity, the AI-prioritized threat landscape, and remediation work
            waiting on human review.
          </p>
        </div>
        <button className="btn btn-primary" onClick={() => navigate("/scans/new")}>
          + New scan
        </button>
      </div>

      <div className="grid grid-4" style={{ marginBottom: 20 }}>
        <div className="panel stat-card">
          <div className="stat-label">Total scans</div>
          <div className="stat-value accent">{scans.length}</div>
        </div>
        <div className="panel stat-card">
          <div className="stat-label">Scans in progress</div>
          <div className="stat-value accent">{inProgressCount}</div>
        </div>
        <div className="panel stat-card">
          <div className="stat-label">Open critical findings</div>
          <div className="stat-value critical">{criticalOpen}</div>
        </div>
        <div className="panel stat-card">
          <div className="stat-label">Remediations pending review</div>
          <div className="stat-value medium">{pendingRemediations?.items?.length ?? 0}</div>
        </div>
      </div>

      <div className="grid grid-2" style={{ marginBottom: 20, alignItems: "start" }}>
        <div className="panel">
          <div className="panel-header">
            <h3>Findings by severity</h3>
            <span className="small-note">across all scans</span>
          </div>
          <div className="panel-pad" style={{ height: 220 }}>
            {pieData.length === 0 ? (
              <EmptyState glyph="◌" title="No findings yet" description="Run a scan to populate the threat matrix." />
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={pieData} dataKey="value" nameKey="name" innerRadius={50} outerRadius={78} paddingAngle={3}>
                    {pieData.map((entry) => (
                      <Cell key={entry.name} fill={SEVERITY_COLORS[entry.name]} stroke="none" />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{ background: "#12192280", border: "1px solid #232e3d", borderRadius: 8, fontSize: 12 }}
                  />
                </PieChart>
              </ResponsiveContainer>
            )}
          </div>
          <div className="panel-pad" style={{ paddingTop: 0, display: "flex", gap: 14, flexWrap: "wrap" }}>
            {pieData.map((entry) => (
              <div key={entry.name} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12 }}>
                <span style={{ width: 8, height: 8, borderRadius: 4, background: SEVERITY_COLORS[entry.name] }} />
                <span className="mono">{entry.name}</span>
                <span style={{ color: "var(--text-faint)" }}>{entry.value}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="panel">
          <div className="panel-header">
            <h3>Findings per scan (trend)</h3>
            <span className="small-note">last 6 completed</span>
          </div>
          <div className="panel-pad" style={{ height: 220 }}>
            {trendData.length === 0 ? (
              <EmptyState glyph="—" title="Not enough history yet" description="Complete a few scans to see a trend." />
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={trendData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1a2330" vertical={false} />
                  <XAxis dataKey="name" tick={{ fontSize: 10, fill: "#93a1b3" }} axisLine={{ stroke: "#232e3d" }} />
                  <YAxis tick={{ fontSize: 10, fill: "#93a1b3" }} axisLine={{ stroke: "#232e3d" }} allowDecimals={false} />
                  <Tooltip
                    contentStyle={{ background: "#121922", border: "1px solid #232e3d", borderRadius: 8, fontSize: 12 }}
                  />
                  <Bar dataKey="findings" fill="#45d6c4" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>
      </div>

      <div className="panel">
        <div className="panel-header">
          <h3>Recent scans</h3>
          <Link to="/scans" className="link-btn">
            View all →
          </Link>
        </div>
        {scansLoading ? (
          <LoadingRow label="Loading scans..." />
        ) : scans.length === 0 ? (
          <EmptyState glyph="▤" title="No scans yet" description="Submit your first authorized target to get started." />
        ) : (
          <div className="scroll-x">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Target</th>
                  <th>Status</th>
                  <th>Active testing</th>
                  <th>Created</th>
                </tr>
              </thead>
              <tbody>
                {scans.slice(0, 6).map((s) => (
                  <tr key={s.scan_id} onClick={() => navigate(`/scans/${s.scan_id}`)}>
                    <td className="mono">{s.target}</td>
                    <td>
                      <StatusPill status={s.status} />
                    </td>
                    <td>{s.active_testing_enabled ? "Enabled" : "Off"}</td>
                    <td className="small-note">{new Date(s.created_at).toLocaleString()}</td>
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
