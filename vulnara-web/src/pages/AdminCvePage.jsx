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
    <div className="p-container-padding max-w-6xl mx-auto flex flex-col gap-6">
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
        <div>
          <h2 className="font-display-lg text-display-lg text-on-surface flex items-center gap-3">
            <span className="material-symbols-outlined text-primary text-[32px]">database</span>
            CVE Definitions
          </h2>
          <p className="text-on-surface-variant mt-2 font-body-md max-w-2xl">
            The locally cached slice of the NVD database that the AI triage step cross-references findings against.
            Synced on a schedule in the background — trigger a manual sync here if you need the latest data right
            now.
          </p>
        </div>
        <button
          className="bg-primary text-on-primary px-4 py-2 rounded-md flex items-center gap-2 font-bold hover:bg-primary/90 transition-colors shadow-[0_0_15px_rgba(200,198,197,0.3)] self-start disabled:opacity-60"
          onClick={() => syncMutation.mutate()}
          disabled={syncMutation.isPending}
        >
          <span className="material-symbols-outlined text-[18px]">sync</span>
          {syncMutation.isPending ? "Syncing..." : "Sync now"}
        </button>
      </div>

      {syncMsg && (
        <div className="flex items-center gap-2 bg-success/10 border border-success/30 text-success rounded-md px-4 py-3 text-sm">
          <span className="material-symbols-outlined text-[18px]">check_circle</span>
          {syncMsg}
        </div>
      )}

      <div className="glass-panel rounded-xl overflow-hidden">
        <div className="p-4 border-b border-outline-variant flex items-center gap-3 flex-wrap bg-surface-container-high/50">
          <div className="relative">
            <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant text-[18px]">search</span>
            <input
              className="bg-[#131313] border border-outline-variant rounded-md py-2 pl-9 pr-3 text-sm text-on-surface font-code-sm placeholder:text-on-surface-variant/50 focus:outline-none focus:border-primary/50 transition-colors w-56"
              placeholder="Search CVE ID..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <select
            className="bg-[#131313] border border-outline-variant rounded-md py-2 px-3 text-sm text-on-surface focus:outline-none focus:border-primary/50 transition-colors"
            value={severity}
            onChange={(e) => setSeverity(e.target.value)}
          >
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
          <EmptyState glyph="database_off" title="No matching CVEs" description="Try clearing the search or severity filter." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse min-w-[900px]">
              <thead className="bg-surface-container-low/50 border-b border-outline-variant">
                <tr>
                  <th className="p-3 pl-6 font-label-caps text-on-surface-variant uppercase tracking-wider">CVE ID</th>
                  <th className="p-3 font-label-caps text-on-surface-variant uppercase tracking-wider">Severity</th>
                  <th className="p-3 font-label-caps text-on-surface-variant uppercase tracking-wider">CVSS v3</th>
                  <th className="p-3 font-label-caps text-on-surface-variant uppercase tracking-wider">Description</th>
                  <th className="p-3 pr-6 font-label-caps text-on-surface-variant uppercase tracking-wider">Published</th>
                </tr>
              </thead>
              <tbody className="font-body-md text-sm">
                {items.map((c) => (
                  <tr key={c.cve_id} className="border-b border-outline-variant/50 data-table-row transition-colors">
                    <td className="p-3 pl-6 font-code-sm text-primary">{c.cve_id}</td>
                    <td className="p-3 text-on-surface-variant">{c.severity}</td>
                    <td className="p-3 font-code-sm text-on-surface-variant">{c.cvss_v3_score ?? "—"}</td>
                    <td className="p-3 text-on-surface-variant max-w-[420px]">{c.description}</td>
                    <td className="p-3 pr-6 text-on-surface-variant text-xs">
                      {c.published_date ? new Date(c.published_date).toLocaleDateString() : "—"}
                    </td>
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
