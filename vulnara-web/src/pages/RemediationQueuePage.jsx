import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { api } from "../lib/api";
import { StatusPill, LoadingRow, EmptyState } from "../components/Primitives";

const STATUSES = ["ALL", "PENDING", "APPROVED", "REJECTED", "EXECUTED"];

export function RemediationQueuePage() {
  const navigate = useNavigate();
  const [status, setStatus] = useState("PENDING");

  const { data, isLoading } = useQuery({
    queryKey: ["remediations", status],
    queryFn: () => api.listAllRemediations({ status: status === "ALL" ? undefined : status }),
  });

  const items = data?.items ?? [];

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1 className="page-title">Remediation queue</h1>
          <p className="page-subtitle">
            Every AI-generated fix, across every scan. Nothing here executes on its own — a human reviews the full
            script and explicitly approves before <span className="mono">mark-executed</span> can even be called.
          </p>
        </div>
      </div>

      <div className="panel">
        <div className="toolbar">
          {STATUSES.map((s) => (
            <button key={s} className={`chip-toggle${status === s ? " active" : ""}`} onClick={() => setStatus(s)}>
              {s}
            </button>
          ))}
        </div>

        {isLoading ? (
          <LoadingRow label="Loading remediation queue..." />
        ) : items.length === 0 ? (
          <EmptyState glyph="✓" title="Nothing here" description="No remediations match this filter right now." />
        ) : (
          <div className="scroll-x">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Remediation</th>
                  <th>Vulnerability</th>
                  <th>Target OS</th>
                  <th>AI confidence</th>
                  <th>Status</th>
                  <th>Created</th>
                </tr>
              </thead>
              <tbody>
                {items.map((r) => (
                  <tr key={r.remediation_id} onClick={() => navigate(`/remediations/${r.remediation_id}`)}>
                    <td className="mono">{r.remediation_id}</td>
                    <td className="mono">{r.vuln_id}</td>
                    <td>{r.target_os || "—"}</td>
                    <td className="mono">{Math.round(r.ai_confidence * 100)}%</td>
                    <td>
                      <StatusPill status={r.status} />
                    </td>
                    <td className="small-note">{new Date(r.created_at).toLocaleString()}</td>
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
