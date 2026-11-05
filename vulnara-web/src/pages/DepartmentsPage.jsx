import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";
import { LoadingRow, EmptyState, ErrorBanner } from "../components/Primitives";

export function DepartmentsPage() {
  const qc = useQueryClient();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState("");

  const { data: departments = [], isLoading: depLoading } = useQuery({
    queryKey: ["departments"],
    queryFn: () => api.listDepartments(),
  });
  const { data: users = [], isLoading: userLoading } = useQuery({
    queryKey: ["admin-users"],
    queryFn: () => api.listUsers(),
  });

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["departments"] });
    qc.invalidateQueries({ queryKey: ["admin-users"] });
  };

  const createMut = useMutation({
    mutationFn: () => api.createDepartment({ name: name.trim(), description: description.trim() || undefined }),
    onSuccess: () => { setName(""); setDescription(""); setError(""); invalidate(); },
    onError: (e) => setError(e.message),
  });
  const deleteMut = useMutation({
    mutationFn: (id) => api.deleteDepartment(id),
    onSuccess: invalidate,
    onError: (e) => setError(e.message),
  });
  const assignMut = useMutation({
    mutationFn: ({ userId, departmentId }) => api.assignUserDepartment(userId, departmentId || null),
    onSuccess: invalidate,
    onError: (e) => setError(e.message),
  });

  const analysts = users.filter((u) => u.role === "analyst");

  return (
    <div className="p-container-padding max-w-6xl mx-auto flex flex-col gap-6">
      <div>
        <h2 className="font-display-lg text-display-lg text-on-surface flex items-center gap-3">
          <span className="material-symbols-outlined text-primary text-[32px]">groups</span>
          Departments
        </h2>
        <p className="text-on-surface-variant mt-2 font-body-md max-w-2xl">
          Create departments and assign analysts. Each analyst sees only their department's scans and activity; admins see everything.
        </p>
      </div>

      <ErrorBanner message={error} />

      {/* Create department */}
      <div className="glass-panel rounded-xl p-5">
        <h3 className="text-sm font-bold text-on-surface uppercase tracking-wider mb-4">New department</h3>
        <form
          className="flex flex-col sm:flex-row gap-3"
          onSubmit={(e) => { e.preventDefault(); if (name.trim()) createMut.mutate(); }}
        >
          <input
            className="flex-1 bg-[#0d1117] border border-outline-variant rounded-lg py-2 px-3 text-sm text-on-surface focus:outline-none focus:border-primary/50"
            placeholder="Department name (e.g. IT Security)"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
          />
          <input
            className="flex-1 bg-[#0d1117] border border-outline-variant rounded-lg py-2 px-3 text-sm text-on-surface focus:outline-none focus:border-primary/50"
            placeholder="Description (optional)"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
          <button
            type="submit"
            disabled={createMut.isPending || !name.trim()}
            className="bg-primary text-primary-container px-4 py-2 rounded-lg font-bold hover:bg-primary/90 transition-colors disabled:opacity-60 flex items-center gap-2 justify-center"
          >
            <span className="material-symbols-outlined text-[18px]">add</span>
            Create
          </button>
        </form>
      </div>

      {/* Departments list */}
      <div className="glass-panel rounded-xl overflow-hidden">
        <div className="p-4 border-b border-outline-variant/40">
          <h3 className="text-sm font-bold text-on-surface uppercase tracking-wider">Departments ({departments.length})</h3>
        </div>
        {depLoading ? (
          <LoadingRow label="Loading departments..." />
        ) : departments.length === 0 ? (
          <EmptyState glyph="groups" title="No departments yet" description="Create one above to start scoping analysts." />
        ) : (
          <div className="divide-y divide-outline-variant/20">
            {departments.map((d) => (
              <div key={d.department_id} className="px-4 py-3 flex items-center justify-between gap-3">
                <div>
                  <div className="text-on-surface font-medium">{d.name}</div>
                  <div className="text-xs text-on-surface-variant">
                    {d.description || "No description"} · {d.member_count} analyst{d.member_count === 1 ? "" : "s"}
                  </div>
                </div>
                <button
                  onClick={() => deleteMut.mutate(d.department_id)}
                  disabled={deleteMut.isPending}
                  className="flex items-center gap-1 px-2.5 py-1 text-xs font-medium text-error bg-error/10 hover:bg-error/20 rounded-lg border border-error/20 transition-colors disabled:opacity-60"
                  title="Delete department (un-assigns its analysts)"
                >
                  <span className="material-symbols-outlined text-[14px]">delete</span>
                  Delete
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Assign analysts */}
      <div className="glass-panel rounded-xl overflow-hidden">
        <div className="p-4 border-b border-outline-variant/40">
          <h3 className="text-sm font-bold text-on-surface uppercase tracking-wider">Analyst assignments</h3>
        </div>
        {userLoading ? (
          <LoadingRow label="Loading analysts..." />
        ) : analysts.length === 0 ? (
          <EmptyState glyph="person" title="No analysts" description="Analysts you add will appear here for assignment." />
        ) : (
          <div className="divide-y divide-outline-variant/20">
            {analysts.map((u) => (
              <div key={u.user_id} className="px-4 py-3 flex items-center justify-between gap-3">
                <div className="min-w-0">
                  <div className="text-on-surface text-sm font-medium truncate">{u.full_name}</div>
                  <div className="text-xs text-on-surface-variant truncate">{u.email}</div>
                </div>
                <select
                  className="bg-[#0d1117] border border-outline-variant rounded-lg py-1.5 px-3 text-sm text-on-surface focus:outline-none focus:border-primary/50 cursor-pointer"
                  value={u.department_id || ""}
                  onChange={(e) => assignMut.mutate({ userId: u.user_id, departmentId: e.target.value })}
                >
                  <option value="">— Unassigned —</option>
                  {departments.map((d) => (
                    <option key={d.department_id} value={d.department_id}>{d.name}</option>
                  ))}
                </select>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
