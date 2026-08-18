import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { api } from "../lib/api";
import { useAuth } from "../context/AuthContext";
import { StatusPill, LoadingRow, EmptyState } from "../components/Primitives";

const STATUS_FILTERS = ["ALL", "PENDING", "IN_PROGRESS", "COMPLETED", "FAILED", "CANCELLED"];

const ROLE_COLORS = {
  admin: "text-red-400",
  analyst: "text-blue-400",
  client: "text-green-400",
};

export function ScansListPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";
  const [status, setStatus] = useState("ALL");
  const [search, setSearch] = useState("");

  const { data, isLoading } = useQuery({
    queryKey: ["scans", status, search],
    queryFn: () => api.listScans({ status: status === "ALL" ? undefined : status, target: search || undefined }),
  });

  const scans = data?.items ?? (Array.isArray(data) ? data : []);

  const filtered = scans.filter((s) => {
    if (status !== "ALL" && s.status !== status) return false;
    if (search && !s.target?.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  return (
    <div className="p-container-padding max-w-7xl mx-auto flex flex-col gap-6">
      <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-4">
        <div>
          <h2 className="font-display-lg text-display-lg text-on-surface">
            {isAdmin ? "All Scans" : "My Scans"}
          </h2>
          <p className="text-on-surface-variant mt-2 font-body-md max-w-2xl">
            {isAdmin
              ? "Every scan across all users — with the initiating user shown for audit purposes."
              : "Every scan Vulnara has run for your account — authorization on record, current status, and active testing."}
          </p>
        </div>
        <div className="flex gap-3">
          <div className="relative">
            <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant text-[18px]">
              search
            </span>
            <input
              className="bg-[#131313] border border-outline-variant rounded-md py-2 pl-9 pr-3 text-sm text-on-surface
                         placeholder:text-on-surface-variant/50 focus:outline-none focus:border-primary/50 transition-colors w-52"
              placeholder="Filter by target..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <button
            onClick={() => navigate("/scans/new")}
            className="bg-primary text-primary-container px-4 py-2 rounded-md flex items-center gap-2 font-bold hover:bg-primary/90 transition-colors shadow-[0_0_15px_rgba(200,198,197,0.3)]"
          >
            <span className="material-symbols-outlined text-[18px]">add</span>
            New Scan
          </button>
        </div>
      </div>

      <div className="glass-panel rounded-xl flex-1 flex flex-col overflow-hidden">
        {/* Status Filters */}
        <div className="p-4 border-b border-outline-variant flex items-center gap-2 flex-wrap bg-surface-container-high/50">
          {STATUS_FILTERS.map((s) => (
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
          {isAdmin && (
            <span className="ml-auto flex items-center gap-1.5 text-[10px] uppercase tracking-wider text-primary bg-primary/10 border border-primary/20 px-2.5 py-1 rounded-full font-bold">
              <span className="material-symbols-outlined text-[12px]">admin_panel_settings</span>
              Admin View — All Users
            </span>
          )}
        </div>

        {isLoading ? (
          <LoadingRow label="Loading scans..." />
        ) : filtered.length === 0 ? (
          <EmptyState glyph="biotech" title="No matching scans" description="Try a different filter, or submit a new scan." />
        ) : (
          <div className="overflow-x-auto flex-1">
            <table className="w-full text-left border-collapse min-w-[800px]">
              <thead className="bg-surface-container-low sticky top-0 z-10">
                <tr>
                  <th className="p-table-cell-padding font-label-caps text-label-caps text-on-surface-variant uppercase tracking-wider border-b border-outline-variant">
                    Target
                  </th>
                  {isAdmin && (
                    <th className="p-table-cell-padding font-label-caps text-label-caps text-on-surface-variant uppercase tracking-wider border-b border-outline-variant">
                      Initiated By
                    </th>
                  )}
                  <th className="p-table-cell-padding font-label-caps text-label-caps text-on-surface-variant uppercase tracking-wider border-b border-outline-variant">
                    Status
                  </th>
                  <th className="p-table-cell-padding font-label-caps text-label-caps text-on-surface-variant uppercase tracking-wider border-b border-outline-variant">
                    Active Testing
                  </th>
                  <th className="p-table-cell-padding font-label-caps text-label-caps text-on-surface-variant uppercase tracking-wider border-b border-outline-variant">
                    Started
                  </th>
                  <th className="p-table-cell-padding font-label-caps text-label-caps text-on-surface-variant uppercase tracking-wider border-b border-outline-variant">
                    Completed
                  </th>
                </tr>
              </thead>
              <tbody className="font-code-sm text-code-sm text-on-surface divide-y divide-outline-variant/30">
                {filtered.map((s) => (
                  <tr
                    key={s.scan_id}
                    onClick={() => navigate(`/scans/${s.scan_id}`)}
                    className="data-table-row transition-colors cursor-pointer group hover:bg-white/[0.02]"
                  >
                    <td className="p-table-cell-padding text-primary font-bold">{s.target}</td>
                    {isAdmin && (
                      <td className="p-table-cell-padding">
                        <div className="flex flex-col">
                          <span className="text-on-surface text-xs font-medium">{s.user_full_name || "—"}</span>
                          <span className="text-on-surface-variant text-[10px]">{s.user_email || ""}</span>
                          {s.user_role && (
                            <span className={`text-[9px] uppercase font-bold tracking-wider mt-0.5 ${ROLE_COLORS[s.user_role] || ""}`}>
                              {s.user_role}
                            </span>
                          )}
                        </div>
                      </td>
                    )}
                    <td className="p-table-cell-padding">
                      <StatusPill status={s.status} />
                    </td>
                    <td className="p-table-cell-padding text-on-surface-variant">
                      {s.active_testing_enabled ? "Enabled" : "Off"}
                    </td>
                    <td className="p-table-cell-padding text-on-surface-variant">
                      {s.started_at ? new Date(s.started_at).toLocaleString() : "—"}
                    </td>
                    <td className="p-table-cell-padding text-on-surface-variant">
                      {s.completed_at ? new Date(s.completed_at).toLocaleString() : "—"}
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
