import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { api } from "../lib/api";
import { StatusPill, LoadingRow, EmptyState } from "../components/Primitives";

const STATUS_FILTERS = ["ALL", "PENDING", "IN_PROGRESS", "COMPLETED", "FAILED", "CANCELLED"];

export function ScansListPage() {
  const navigate = useNavigate();
  const [status, setStatus] = useState("ALL");
  const [search, setSearch] = useState("");

  const { data, isLoading } = useQuery({
    queryKey: ["scans", status, search],
    queryFn: () => api.listScans({ status: status === "ALL" ? undefined : status, target: search || undefined }),
  });

  const scans = data?.items ?? [];

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1 className="page-title">Scans</h1>
          <p className="page-subtitle">
            Every scan Vulnara has run for your account — the authorization on record, current status, and
            whether active payload testing was enabled.
          </p>
        </div>
        <button className="btn btn-primary" onClick={() => navigate("/scans/new")}>
          + New scan
        </button>
      </div>

      <div className="panel">
        <div className="toolbar">
          {STATUS_FILTERS.map((s) => (
            <button key={s} className={`chip-toggle${status === s ? " active" : ""}`} onClick={() => setStatus(s)}>
              {s}
            </button>
          ))}
          <div className="spacer" />
          <input
            className="input"
            style={{ maxWidth: 220 }}
            placeholder="Filter by target..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        {isLoading ? (
          <LoadingRow label="Loading scans..." />
        ) : scans.length === 0 ? (
          <EmptyState glyph="▤" title="No matching scans" description="Try a different filter, or submit a new scan." />
        ) : (
          <div className="scroll-x">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Target</th>
                  <th>Status</th>
                  <th>Active testing</th>
                  <th>Started</th>
                  <th>Completed</th>
                </tr>
              </thead>
              <tbody>
                {scans.map((s) => (
                  <tr key={s.scan_id} onClick={() => navigate(`/scans/${s.scan_id}`)}>
                    <td className="mono">{s.target}</td>
                    <td>
                      <StatusPill status={s.status} />
                    </td>
                    <td>{s.active_testing_enabled ? "Enabled" : "Off"}</td>
                    <td className="small-note">{s.started_at ? new Date(s.started_at).toLocaleString() : "—"}</td>
                    <td className="small-note">{s.completed_at ? new Date(s.completed_at).toLocaleString() : "—"}</td>
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
