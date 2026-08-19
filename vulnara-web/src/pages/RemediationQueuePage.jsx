import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { api } from "../lib/api";
import { useAuth } from "../context/AuthContext";
import { StatusPill, ConfidenceBar, LoadingRow, EmptyState } from "../components/Primitives";

const STATUSES = ["ALL", "PENDING", "APPROVED", "REJECTED", "EXECUTED"];

export function RemediationQueuePage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const isClient = user?.role === "client";
  const [status, setStatus] = useState("PENDING");

  const { data, isLoading } = useQuery({
    queryKey: ["remediations", status],
    queryFn: () => api.listAllRemediations({ status: status === "ALL" ? undefined : status }),
  });

  const items = data?.items ?? [];

  return (
    <div className="p-container-padding max-w-7xl mx-auto flex flex-col gap-6">
      <div>
        <h2 className="font-display-lg text-display-lg text-on-surface">Remediation Queue</h2>
        <p className="text-on-surface-variant mt-2 font-body-md max-w-2xl">
          {isClient
            ? "AI-generated fixes for your own scans. Nothing here executes on its own — once an analyst approves a script, apply it and use "
            : "Every AI-generated fix, across every scan. Nothing here executes on its own — a human reviews the full script and explicitly approves before "}
          <span className="font-code-sm text-primary">mark-executed</span>
          {isClient ? " to record it." : " can even be called."}
        </p>
      </div>

      <div className="glass-panel rounded-xl flex-1 flex flex-col overflow-hidden">
        <div className="p-4 border-b border-outline-variant flex items-center gap-2 flex-wrap bg-surface-container-high/50">
          {STATUSES.map((s) => (
            <button
              key={s}
              onClick={() => setStatus(s)}
              className={`px-3 py-1.5 rounded text-xs font-bold font-code-sm transition-colors border ${
                status === s
                  ? "bg-primary/20 border-primary/50 text-primary"
                  : "bg-surface-variant border-outline-variant text-on-surface-variant hover:bg-surface-variant/80"
              }`}
            >
              {s}
            </button>
          ))}
        </div>

        {isLoading ? (
          <LoadingRow label="Loading remediation queue..." />
        ) : items.length === 0 ? (
          <EmptyState glyph="task_alt" title="Nothing here" description="No remediations match this filter right now." />
        ) : (
          <div className="overflow-x-auto flex-1">
            <table className="w-full text-left border-collapse min-w-[800px]">
              <thead className="bg-surface-container-low sticky top-0 z-10">
                <tr>
                  <th className="p-table-cell-padding font-label-caps text-label-caps text-on-surface-variant uppercase tracking-wider border-b border-outline-variant">Remediation</th>
                  <th className="p-table-cell-padding font-label-caps text-label-caps text-on-surface-variant uppercase tracking-wider border-b border-outline-variant">Vulnerability</th>
                  <th className="p-table-cell-padding font-label-caps text-label-caps text-on-surface-variant uppercase tracking-wider border-b border-outline-variant">Target OS</th>
                  <th className="p-table-cell-padding font-label-caps text-label-caps text-on-surface-variant uppercase tracking-wider border-b border-outline-variant">AI confidence</th>
                  <th className="p-table-cell-padding font-label-caps text-label-caps text-on-surface-variant uppercase tracking-wider border-b border-outline-variant">Status</th>
                  <th className="p-table-cell-padding font-label-caps text-label-caps text-on-surface-variant uppercase tracking-wider border-b border-outline-variant">Created</th>
                </tr>
              </thead>
              <tbody className="font-code-sm text-code-sm text-on-surface divide-y divide-outline-variant/30">
                {items.map((r) => (
                  <tr key={r.remediation_id} onClick={() => navigate(`/remediations/${r.remediation_id}`)} className="data-table-row transition-colors cursor-pointer group">
                    <td className="p-table-cell-padding text-primary font-bold">{r.remediation_id}</td>
                    <td className="p-table-cell-padding text-on-surface-variant">{r.vuln_id}</td>
                    <td className="p-table-cell-padding text-on-surface-variant">{r.target_os || "—"}</td>
                    <td className="p-table-cell-padding"><ConfidenceBar value={r.ai_confidence} /></td>
                    <td className="p-table-cell-padding"><StatusPill status={r.status} /></td>
                    <td className="p-table-cell-padding text-on-surface-variant">{new Date(r.created_at).toLocaleString()}</td>
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
