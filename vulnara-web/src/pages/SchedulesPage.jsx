import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";
import { LoadingRow, EmptyState, ErrorBanner } from "../components/Primitives";

const INTERVALS = [
  { label: "Every 15 minutes", value: 15 },
  { label: "Hourly", value: 60 },
  { label: "Every 6 hours", value: 360 },
  { label: "Daily", value: 1440 },
  { label: "Weekly", value: 10080 },
];

function intervalLabel(m) {
  return INTERVALS.find((i) => i.value === m)?.label || `Every ${m} min`;
}

export function SchedulesPage() {
  const qc = useQueryClient();
  const [target, setTarget] = useState("");
  const [interval, setInterval] = useState(1440);
  const [activeTesting, setActiveTesting] = useState(false);
  const [authorized, setAuthorized] = useState(false);
  const [justification, setJustification] = useState("");
  const [error, setError] = useState("");

  const { data: schedules = [], isLoading } = useQuery({
    queryKey: ["schedules"],
    queryFn: () => api.listSchedules(),
  });
  const invalidate = () => qc.invalidateQueries({ queryKey: ["schedules"] });

  const createMut = useMutation({
    mutationFn: () => api.createSchedule({
      target: target.trim(),
      authorization_confirmed: authorized,
      authorization_justification: justification.trim(),
      active_testing_enabled: activeTesting,
      interval_minutes: interval,
    }),
    onSuccess: () => {
      setTarget(""); setJustification(""); setAuthorized(false); setActiveTesting(false); setError("");
      invalidate();
    },
    onError: (e) => setError(e.message),
  });
  const toggleMut = useMutation({
    mutationFn: ({ id, enabled }) => api.toggleSchedule(id, enabled),
    onSuccess: invalidate,
  });
  const deleteMut = useMutation({
    mutationFn: (id) => api.deleteSchedule(id),
    onSuccess: invalidate,
  });

  const canCreate = target.trim() && authorized && justification.trim().length >= 10;

  return (
    <div className="p-container-padding max-w-5xl mx-auto flex flex-col gap-6">
      <div>
        <h2 className="font-display-lg text-display-lg text-on-surface flex items-center gap-3">
          <span className="material-symbols-outlined text-primary text-[32px]">schedule</span>
          Scheduled Scans
        </h2>
        <p className="text-on-surface-variant mt-2 font-body-md max-w-2xl">
          Automatically re-scan a target on a recurring interval — continuous monitoring. Each run is tagged to your department, just like a manual scan.
        </p>
      </div>

      <ErrorBanner message={error} />

      {/* New schedule */}
      <div className="glass-panel rounded-xl p-5 flex flex-col gap-4">
        <h3 className="text-sm font-bold text-on-surface uppercase tracking-wider">New schedule</h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <input
            className="bg-[#0d1117] border border-outline-variant rounded-lg py-2 px-3 text-sm text-on-surface focus:outline-none focus:border-primary/50"
            placeholder="Target (IP, domain, or URL)"
            value={target}
            onChange={(e) => setTarget(e.target.value)}
          />
          <select
            className="bg-[#0d1117] border border-outline-variant rounded-lg py-2 px-3 text-sm text-on-surface focus:outline-none focus:border-primary/50 cursor-pointer"
            value={interval}
            onChange={(e) => setInterval(Number(e.target.value))}
          >
            {INTERVALS.map((i) => <option key={i.value} value={i.value}>{i.label}</option>)}
          </select>
        </div>
        <textarea
          className="bg-[#0d1117] border border-outline-variant rounded-lg py-2 px-3 text-sm text-on-surface focus:outline-none focus:border-primary/50"
          rows={2}
          placeholder="Authorization justification (why you're permitted to scan this target) — min 10 characters"
          value={justification}
          onChange={(e) => setJustification(e.target.value)}
        />
        <div className="flex flex-wrap items-center gap-5">
          <label className="flex items-center gap-2 text-sm text-on-surface-variant cursor-pointer">
            <input type="checkbox" checked={activeTesting} onChange={(e) => setActiveTesting(e.target.checked)} />
            Active AI testing
          </label>
          <label className="flex items-center gap-2 text-sm text-on-surface-variant cursor-pointer">
            <input type="checkbox" checked={authorized} onChange={(e) => setAuthorized(e.target.checked)} />
            I confirm I'm authorized to scan this target
          </label>
          <button
            onClick={() => createMut.mutate()}
            disabled={!canCreate || createMut.isPending}
            className="ml-auto bg-primary text-primary-container px-4 py-2 rounded-lg font-bold hover:bg-primary/90 transition-colors disabled:opacity-50 flex items-center gap-2"
          >
            <span className="material-symbols-outlined text-[18px]">add_alarm</span>
            Schedule
          </button>
        </div>
      </div>

      {/* Schedules list */}
      <div className="glass-panel rounded-xl overflow-hidden">
        <div className="p-4 border-b border-outline-variant/40">
          <h3 className="text-sm font-bold text-on-surface uppercase tracking-wider">Active schedules ({schedules.length})</h3>
        </div>
        {isLoading ? (
          <LoadingRow label="Loading schedules..." />
        ) : schedules.length === 0 ? (
          <EmptyState glyph="schedule" title="No schedules yet" description="Create one above for continuous monitoring." />
        ) : (
          <div className="divide-y divide-outline-variant/20">
            {schedules.map((s) => (
              <div key={s.schedule_id} className="px-4 py-3 flex items-center justify-between gap-3">
                <div className="min-w-0">
                  <div className="text-on-surface text-sm font-code-sm truncate">{s.target}</div>
                  <div className="text-xs text-on-surface-variant">
                    {intervalLabel(s.interval_minutes)}
                    {s.active_testing_enabled ? " · active testing" : ""}
                    {" · next run "}{s.next_run_at ? new Date(s.next_run_at).toLocaleString() : "—"}
                    {s.last_run_at ? ` · last ${new Date(s.last_run_at).toLocaleString()}` : ""}
                  </div>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <button
                    onClick={() => toggleMut.mutate({ id: s.schedule_id, enabled: !s.enabled })}
                    className={`px-2.5 py-1 text-xs font-medium rounded-lg border transition-colors ${
                      s.enabled
                        ? "text-green-400 bg-green-400/10 border-green-400/20"
                        : "text-on-surface-variant bg-surface-variant border-outline-variant"
                    }`}
                  >
                    {s.enabled ? "Enabled" : "Paused"}
                  </button>
                  <button
                    onClick={() => deleteMut.mutate(s.schedule_id)}
                    className="flex items-center gap-1 px-2.5 py-1 text-xs font-medium text-error bg-error/10 hover:bg-error/20 rounded-lg border border-error/20 transition-colors"
                  >
                    <span className="material-symbols-outlined text-[14px]">delete</span>
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
