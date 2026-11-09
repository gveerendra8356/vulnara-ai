import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";

// Relative "x ago" label from an ISO timestamp.
function relativeTime(iso) {
  const ts = new Date(iso).getTime();
  if (Number.isNaN(ts)) return "";
  const diff = Date.now() - ts;
  const m = Math.floor(diff / 60000);
  if (m < 1) return "just now";
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  const d = Math.floor(h / 24);
  if (d < 7) return `${d}d ago`;
  return `${Math.floor(d / 7)}w ago`;
}

function unwrap(res) {
  if (Array.isArray(res)) return res;
  if (res && Array.isArray(res.items)) return res.items;
  return [];
}

// The web Alerts feed, synthesised from real backend data (scans +
// remediations) exactly like the mobile app's Alerts Hub. Both source
// endpoints are already department-scoped on the backend, so an analyst
// only ever sees their own department's activity here.
function buildNotifications(scans, remediations) {
  const out = [];

  for (const s of scans) {
    const status = String(s.status || "").toUpperCase();
    const counts = s.vuln_count_by_severity || null;
    const critical = counts ? Number(counts.CRITICAL || 0) : 0;

    if (status === "COMPLETED") {
      if (critical > 0) {
        out.push({
          id: `crit-${s.scan_id}`,
          symbol: "warning",
          tone: "error",
          title: "Critical Vulnerability Detected",
          body: `${critical} critical finding${critical > 1 ? "s" : ""} on ${s.target}.`,
          time: s.created_at,
          route: `/scans/${s.scan_id}`,
          critical: true,
        });
      }
      out.push({
        id: `scan-done-${s.scan_id}`,
        symbol: "check_circle",
        tone: "success",
        title: "Scan Completed",
        body: `Scan of ${s.target} finished${counts ? ` with ${Object.values(counts).reduce((a, b) => a + Number(b || 0), 0)} findings` : ""}.`,
        time: s.created_at,
        route: `/scans/${s.scan_id}`,
      });
    } else if (status === "FAILED") {
      out.push({
        id: `scan-fail-${s.scan_id}`,
        symbol: "error",
        tone: "error",
        title: "Scan Failed",
        body: `The scan of ${s.target} did not complete.`,
        time: s.created_at,
        route: `/scans/${s.scan_id}`,
      });
    }
  }

  for (const r of remediations) {
    const status = String(r.status || "").toUpperCase();
    const summary = r.executive_summary || "AI remediation";
    const short = summary.length > 110 ? `${summary.slice(0, 110)}…` : summary;
    const base = { time: r.created_at, route: `/remediations/${r.remediation_id}`, body: short };
    if (status === "PENDING") {
      out.push({ ...base, id: `rem-pending-${r.remediation_id}`, symbol: "hourglass_top", tone: "muted", title: "Remediation Awaiting Review" });
    } else if (status === "APPROVED") {
      out.push({ ...base, id: `rem-approved-${r.remediation_id}`, symbol: "verified", tone: "primary", title: "Remediation Approved" });
    } else if (status === "EXECUTED") {
      out.push({ ...base, id: `rem-executed-${r.remediation_id}`, symbol: "rocket_launch", tone: "success", title: "Remediation Executed" });
    }
  }

  out.sort((a, b) => new Date(b.time).getTime() - new Date(a.time).getTime());
  return out.slice(0, 30);
}

const TONE = {
  error: "text-error",
  success: "text-success",
  primary: "text-primary",
  muted: "text-on-surface-variant",
};

export function NotificationsBell() {
  const [open, setOpen] = useState(false);
  const [criticalOnly, setCriticalOnly] = useState(false);
  const wrapRef = useRef(null);
  const navigate = useNavigate();

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["notifications-feed"],
    queryFn: async () => {
      const [scansRes, remsRes] = await Promise.all([
        api.listScans(),
        api.listAllRemediations(),
      ]);
      return buildNotifications(unwrap(scansRes), unwrap(remsRes));
    },
    staleTime: 30_000,
    refetchInterval: 60_000,
  });

  const notifications = useMemo(() => data || [], [data]);
  const visible = criticalOnly ? notifications.filter((n) => n.critical) : notifications;
  const hasUnseen = notifications.length > 0;

  // Close on outside click / Escape.
  useEffect(() => {
    if (!open) return undefined;
    const onDown = (e) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target)) setOpen(false);
    };
    const onKey = (e) => e.key === "Escape" && setOpen(false);
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const openNotification = (n) => {
    setOpen(false);
    if (n.route) navigate(n.route);
  };

  return (
    <div className="relative" ref={wrapRef}>
      <button
        type="button"
        aria-label="Notifications"
        aria-haspopup="true"
        aria-expanded={open}
        onClick={() => {
          setOpen((v) => !v);
          if (!open) refetch();
        }}
        className="text-on-surface-variant hover:text-primary transition-all p-2 rounded-full hover:bg-surface-variant/50 relative"
      >
        <span className="material-symbols-outlined">notifications</span>
        {hasUnseen && (
          <span className="absolute top-1.5 right-1.5 min-w-[16px] h-4 px-1 rounded-full bg-error text-[10px] font-bold text-white flex items-center justify-center leading-none">
            {notifications.length > 9 ? "9+" : notifications.length}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 mt-2 w-[360px] max-w-[92vw] bg-surface-container border border-outline-variant rounded-xl shadow-2xl z-50 overflow-hidden">
          <div className="flex items-center justify-between px-4 py-3 border-b border-outline-variant/60">
            <span className="font-bold text-on-surface">Notifications</span>
            <div className="flex items-center gap-1">
              {["ALL", "CRITICAL"].map((label) => {
                const sel = (label === "CRITICAL") === criticalOnly;
                return (
                  <button
                    key={label}
                    type="button"
                    onClick={() => setCriticalOnly(label === "CRITICAL")}
                    className={`text-[10px] font-label-caps uppercase tracking-wider px-2 py-1 rounded-full border transition-colors ${
                      sel
                        ? "bg-surface-variant text-on-surface border-outline-variant"
                        : "text-on-surface-variant/70 border-transparent hover:text-on-surface"
                    }`}
                  >
                    {label}
                  </button>
                );
              })}
            </div>
          </div>

          <div className="max-h-[70vh] overflow-y-auto">
            {isLoading ? (
              <div className="px-4 py-8 text-center text-sm text-on-surface-variant">Loading…</div>
            ) : isError ? (
              <div className="px-4 py-8 text-center text-sm text-error">
                Couldn’t load notifications.
                <button type="button" onClick={() => refetch()} className="block mx-auto mt-2 text-primary underline">
                  Retry
                </button>
              </div>
            ) : visible.length === 0 ? (
              <div className="px-4 py-10 text-center text-sm text-on-surface-variant">
                <span className="material-symbols-outlined text-3xl opacity-40 block mb-2">
                  {criticalOnly ? "shield" : "notifications_off"}
                </span>
                {criticalOnly ? "No critical alerts." : "No notifications yet."}
              </div>
            ) : (
              <ul className="divide-y divide-outline-variant/40">
                {visible.map((n) => (
                  <li key={n.id}>
                    <button
                      type="button"
                      onClick={() => openNotification(n)}
                      className={`w-full text-left px-4 py-3 flex gap-3 hover:bg-surface-variant/40 transition-colors ${
                        n.critical ? "border-l-2 border-error" : ""
                      }`}
                    >
                      <span className={`material-symbols-outlined text-[20px] shrink-0 ${TONE[n.tone] || TONE.muted}`}>
                        {n.symbol}
                      </span>
                      <span className="min-w-0 flex-1">
                        <span className="flex items-center justify-between gap-2">
                          <span className="font-semibold text-sm text-on-surface truncate">{n.title}</span>
                          <span className={`text-[10px] font-label-caps uppercase tracking-wider shrink-0 ${n.critical ? "text-error" : "text-on-surface-variant/70"}`}>
                            {relativeTime(n.time)}
                          </span>
                        </span>
                        <span className="block text-xs text-on-surface-variant mt-0.5 line-clamp-2">{n.body}</span>
                      </span>
                      <span className="material-symbols-outlined text-[16px] text-on-surface-variant/50 self-center">
                        chevron_right
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
