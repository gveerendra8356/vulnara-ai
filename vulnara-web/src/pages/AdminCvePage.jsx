import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";
import { LoadingRow, EmptyState } from "../components/Primitives";

const SEVERITIES = ["", "CRITICAL", "HIGH", "MEDIUM", "LOW", "NONE"];

export function AdminCvePage() {
  const qc = useQueryClient();
  const [search, setSearch] = useState("");
  const [severity, setSeverity] = useState("");
  const [syncMsg, setSyncMsg] = useState("");

  const { data, isLoading } = useQuery({
    queryKey: ["admin-cve", search, severity],
    queryFn: () => api.listCveDefs({ cve_id: search || undefined, severity: severity || undefined }),
  });

  const syncMutation = useMutation({
    mutationFn: () => api.syncCveDefs(),
    onSuccess: (res) => {
      setSyncMsg(`Sync job ${res.sync_job_id} started.`);
      qc.invalidateQueries({ queryKey: ["admin-cve"] });
      setTimeout(() => setSyncMsg(""), 4000);
    },
  });

  const items = data?.items ?? [];

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1 className="page-title">CVE definitions</h1>
          <p className="page-subtitle">
            The locally cached slice of the NVD database that the AI triage step cross-references findings against.
            Synced on a schedule in the background — trigger a manual sync here if you need the latest data right
            now.
          </p>
        </div>
        <button className="btn btn-primary" onClick={() => syncMutation.mutate()} disabled={syncMutation.isPending}>
          {syncMutation.isPending ? "Syncing..." : "Sync now"}
        </button>
      </div>

      {syncMsg && (
        <div className="warn-box" style={{ marginBottom: 16, background: "var(--success-wash)", borderColor: "var(--success)", color: "#c9f9df" }}>
          <span>✓</span>
          <span>{syncMsg}</span>
        </div>
      )}

      <div className="panel">
        <div className="toolbar">
          <input className="input mono" style={{ maxWidth: 220 }} placeholder="Search CVE ID..." value={search} onChange={(e) => setSearch(e.target.value)} />
          <select className="select" style={{ maxWidth: 160 }} value={severity} onChange={(e) => setSeverity(e.target.value)}>
            {SEVERITIES.map((s) => (
              <option key={s || "any"} value={s}>
                {s || "All severities"}
              </option>
            ))}
          </select>
        </div>

        {isLoading ? (
          <LoadingRow label="Loading CVE cache..." />
        ) : items.length === 0 ? (
          <EmptyState glyph="◎" title="No matching CVEs" description="Try clearing the search or severity filter." />
        ) : (
          <div className="scroll-x">
            <table className="data-table">
              <thead>
                <tr>
                  <th>CVE ID</th>
                  <th>Severity</th>
                  <th>CVSS v3</th>
                  <th>Description</th>
                  <th>Published</th>
                </tr>
              </thead>
              <tbody>
                {items.map((c) => (
                  <tr key={c.cve_id} style={{ cursor: "default" }}>
                    <td className="mono">{c.cve_id}</td>
                    <td>{c.severity}</td>
                    <td className="mono">{c.cvss_v3_score ?? "—"}</td>
                    <td style={{ maxWidth: 420 }}>{c.description}</td>
                    <td className="small-note">{c.published_date ? new Date(c.published_date).toLocaleDateString() : "—"}</td>
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
