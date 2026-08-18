import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { api } from "../lib/api";
import { LoadingRow, EmptyState } from "../components/Primitives";

const ROLE_BADGE = {
  admin: "bg-red-500/15 text-red-400 border border-red-500/30",
  analyst: "bg-blue-500/15 text-blue-400 border border-blue-500/30",
  client: "bg-green-500/15 text-green-400 border border-green-500/30",
};

function UserDetailPanel({ userId, onClose }) {
  const { data, isLoading } = useQuery({
    queryKey: ["admin-user-scans", userId],
    queryFn: () => api.getUserScans(userId),
    enabled: !!userId,
  });

  const STATUS_COLORS = {
    COMPLETED: "text-green-400",
    IN_PROGRESS: "text-blue-400",
    FAILED: "text-red-400",
    PENDING: "text-yellow-400",
    CANCELLED: "text-on-surface-variant",
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div
        className="glass-panel rounded-2xl w-full max-w-3xl max-h-[80vh] flex flex-col overflow-hidden border border-outline-variant"
        style={{ boxShadow: "0 0 60px rgba(0,0,0,0.6)" }}
      >
        {/* Header */}
        <div className="p-6 border-b border-outline-variant/30 flex items-start justify-between bg-surface-container-low/50">
          <div>
            {isLoading ? (
              <div className="h-5 w-48 bg-surface-variant rounded animate-pulse" />
            ) : (
              <>
                <h3 className="text-on-surface font-semibold text-lg">{data?.user?.full_name}</h3>
                <p className="text-on-surface-variant text-sm mt-0.5">{data?.user?.email}</p>
                <span className={`text-[10px] uppercase tracking-widest font-bold px-2 py-0.5 rounded-full mt-2 inline-block ${ROLE_BADGE[data?.user?.role] || ROLE_BADGE.client}`}>
                  {data?.user?.role}
                </span>
              </>
            )}
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-full hover:bg-surface-variant/60 text-on-surface-variant transition-colors"
          >
            <span className="material-symbols-outlined text-[20px]">close</span>
          </button>
        </div>

        {/* Scan list */}
        <div className="overflow-y-auto flex-1">
          {isLoading ? (
            <LoadingRow label="Loading scans…" />
          ) : !data?.scans?.length ? (
            <EmptyState glyph="biotech" title="No scans yet" description="This user hasn't run any scans." />
          ) : (
            <table className="w-full text-left text-sm">
              <thead className="sticky top-0 bg-surface-container-low border-b border-outline-variant">
                <tr>
                  <th className="px-6 py-3 text-[10px] uppercase tracking-wider text-on-surface-variant font-semibold">Target</th>
                  <th className="px-4 py-3 text-[10px] uppercase tracking-wider text-on-surface-variant font-semibold">Status</th>
                  <th className="px-4 py-3 text-[10px] uppercase tracking-wider text-on-surface-variant font-semibold">Created</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-outline-variant/20">
                {data.scans.map((s) => (
                  <tr key={s.scan_id} className="hover:bg-white/[0.02] transition-colors">
                    <td className="px-6 py-3 font-mono text-primary text-xs">{s.target}</td>
                    <td className="px-4 py-3">
                      <span className={`text-xs font-bold uppercase ${STATUS_COLORS[s.status] || "text-on-surface-variant"}`}>
                        {s.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-on-surface-variant text-xs">
                      {new Date(s.created_at).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}

export function AdminUsersPage() {
  const qc = useQueryClient();
  const [selectedUserId, setSelectedUserId] = useState(null);
  const [roleFilter, setRoleFilter] = useState("ALL");
  const [search, setSearch] = useState("");

  const { data: users = [], isLoading } = useQuery({
    queryKey: ["admin-users"],
    queryFn: () => api.listUsers(),
  });

  const toggleMutation = useMutation({
    mutationFn: ({ userId, isActive }) => api.toggleUserActive(userId, isActive),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin-users"] }),
  });

  const filtered = users.filter((u) => {
    const matchRole = roleFilter === "ALL" || u.role === roleFilter;
    const matchSearch =
      !search ||
      u.full_name?.toLowerCase().includes(search.toLowerCase()) ||
      u.email?.toLowerCase().includes(search.toLowerCase());
    return matchRole && matchSearch;
  });

  const totalUsers = users.length;
  const activeUsers = users.filter((u) => u.is_active).length;
  const adminCount = users.filter((u) => u.role === "admin").length;
  const analystCount = users.filter((u) => u.role === "analyst").length;
  const clientCount = users.filter((u) => u.role === "client").length;

  return (
    <div className="p-container-padding max-w-7xl mx-auto flex flex-col gap-6">
      {selectedUserId && (
        <UserDetailPanel userId={selectedUserId} onClose={() => setSelectedUserId(null)} />
      )}

      {/* Header */}
      <div>
        <h2 className="font-display-lg text-display-lg text-on-surface flex items-center gap-3">
          <span className="material-symbols-outlined text-primary text-[32px]">group</span>
          User Management
        </h2>
        <p className="text-on-surface-variant mt-2 font-body-md max-w-2xl">
          View all registered users, their roles, scan history, and manage account access.
        </p>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: "Total Users", value: totalUsers, icon: "group", color: "text-primary" },
          { label: "Active", value: activeUsers, icon: "check_circle", color: "text-green-400" },
          { label: "Analysts", value: analystCount, icon: "analytics", color: "text-blue-400" },
          { label: "Clients", value: clientCount, icon: "person", color: "text-purple-400" },
        ].map(({ label, value, icon, color }) => (
          <div key={label} className="glass-panel rounded-xl p-4 flex items-center gap-3">
            <span className={`material-symbols-outlined text-[24px] ${color}`} style={{ fontVariationSettings: "'FILL' 1" }}>
              {icon}
            </span>
            <div>
              <div className="text-xl font-bold text-on-surface">{value}</div>
              <div className="text-[11px] text-on-surface-variant">{label}</div>
            </div>
          </div>
        ))}
      </div>

      {/* Filters */}
      <div className="glass-panel rounded-xl overflow-hidden">
        <div className="p-4 border-b border-outline-variant/30 flex flex-wrap items-center gap-3 bg-surface-container-high/40">
          {/* Role tabs */}
          <div className="flex gap-2">
            {["ALL", "admin", "analyst", "client"].map((r) => (
              <button
                key={r}
                onClick={() => setRoleFilter(r)}
                className={`px-3 py-1.5 rounded text-xs font-bold uppercase tracking-wider transition-colors border ${
                  roleFilter === r
                    ? "bg-primary/20 border-primary/50 text-primary"
                    : "bg-surface-variant border-outline-variant text-on-surface-variant hover:bg-surface-variant/80"
                }`}
              >
                {r}
              </button>
            ))}
          </div>
          {/* Search */}
          <div className="relative ml-auto">
            <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant text-[16px]">
              search
            </span>
            <input
              className="bg-[#0d1117] border border-outline-variant rounded-lg py-1.5 pl-9 pr-3 text-sm text-on-surface
                         placeholder:text-on-surface-variant/40 focus:outline-none focus:border-primary/50 w-52"
              placeholder="Search name or email…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
        </div>

        {/* Table */}
        {isLoading ? (
          <LoadingRow label="Loading users…" />
        ) : filtered.length === 0 ? (
          <EmptyState glyph="person_search" title="No users found" description="Try a different filter." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse min-w-[700px]">
              <thead className="bg-surface-container-low/60 border-b border-outline-variant">
                <tr>
                  {["User", "Role", "Scans", "Last Login", "Status", "Actions"].map((h) => (
                    <th key={h} className="px-5 py-3 text-[10px] uppercase tracking-wider text-on-surface-variant font-semibold">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-outline-variant/20">
                {filtered.map((u) => (
                  <tr
                    key={u.user_id}
                    className="hover:bg-white/[0.02] transition-colors group"
                  >
                    {/* User */}
                    <td className="px-5 py-3.5">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full bg-primary/10 border border-primary/20 flex items-center justify-center text-xs font-bold text-primary shrink-0">
                          {u.full_name?.slice(0, 1)?.toUpperCase() || "?"}
                        </div>
                        <div>
                          <div className="text-on-surface text-sm font-medium">{u.full_name}</div>
                          <div className="text-on-surface-variant text-xs">{u.email}</div>
                        </div>
                      </div>
                    </td>
                    {/* Role */}
                    <td className="px-5 py-3.5">
                      <span className={`text-[10px] uppercase tracking-wider font-bold px-2.5 py-1 rounded-full ${ROLE_BADGE[u.role] || ROLE_BADGE.client}`}>
                        {u.role}
                      </span>
                    </td>
                    {/* Scans */}
                    <td className="px-5 py-3.5 text-on-surface text-sm font-mono">{u.scan_count}</td>
                    {/* Last Login */}
                    <td className="px-5 py-3.5 text-on-surface-variant text-xs">
                      {u.last_login_at ? new Date(u.last_login_at).toLocaleString() : "Never"}
                    </td>
                    {/* Status */}
                    <td className="px-5 py-3.5">
                      <span className={`flex items-center gap-1.5 text-xs font-semibold ${u.is_active ? "text-green-400" : "text-on-surface-variant"}`}>
                        <span className={`w-1.5 h-1.5 rounded-full ${u.is_active ? "bg-green-400" : "bg-on-surface-variant"}`} />
                        {u.is_active ? "Active" : "Disabled"}
                      </span>
                    </td>
                    {/* Actions */}
                    <td className="px-5 py-3.5">
                      <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                        <button
                          onClick={() => setSelectedUserId(u.user_id)}
                          className="flex items-center gap-1 px-2.5 py-1 text-xs font-medium text-primary bg-primary/10 hover:bg-primary/20 rounded-lg transition-colors border border-primary/20"
                        >
                          <span className="material-symbols-outlined text-[14px]">biotech</span>
                          Scans
                        </button>
                        <button
                          onClick={() => toggleMutation.mutate({ userId: u.user_id, isActive: !u.is_active })}
                          disabled={toggleMutation.isPending}
                          className={`flex items-center gap-1 px-2.5 py-1 text-xs font-medium rounded-lg transition-colors border ${
                            u.is_active
                              ? "text-error bg-error/10 hover:bg-error/20 border-error/20"
                              : "text-green-400 bg-green-400/10 hover:bg-green-400/20 border-green-400/20"
                          }`}
                        >
                          <span className="material-symbols-outlined text-[14px]">
                            {u.is_active ? "block" : "check_circle"}
                          </span>
                          {u.is_active ? "Disable" : "Enable"}
                        </button>
                      </div>
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
