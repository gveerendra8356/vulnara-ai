// Shared visual primitives for the Vulnara console. Kept intentionally
// dependency-free (no new libs) so every page can lean on the same
// severity/status language the Stitch UI defines.

const SEVERITY_CLASSES = {
  CRITICAL: "bg-critical text-white shadow-[0_0_8px_rgba(220,38,38,0.4)]",
  HIGH: "bg-high/20 text-high border border-high/30",
  MEDIUM: "bg-medium/20 text-medium border border-medium/30",
  LOW: "bg-low/20 text-low border border-low/30",
  INFO: "bg-info/20 text-info border border-info/30",
};

export function SeverityBadge({ severity }) {
  const cls = SEVERITY_CLASSES[severity] || SEVERITY_CLASSES.INFO;
  return (
    <span
      className={`inline-flex items-center justify-center gap-1 px-2 py-1 rounded font-label-caps text-label-caps text-[10px] uppercase whitespace-nowrap ${cls}`}
    >
      {severity}
    </span>
  );
}

const STATUS_CLASSES = {
  PENDING: "bg-low/20 text-low border border-low/30",
  IN_PROGRESS: "bg-low/20 text-low border border-low/30",
  COMPLETED: "bg-success/10 text-success border border-success/20",
  FAILED: "bg-critical text-white shadow-[0_0_10px_rgba(220,38,38,0.4)]",
  CANCELLED: "bg-surface-variant text-on-surface-variant border border-outline-variant",
  OPEN: "bg-high/20 text-high border border-high/30",
  REMEDIATED: "bg-success/10 text-success border border-success/20",
  ACCEPTED_RISK: "bg-medium/20 text-medium border border-medium/30",
  FALSE_POSITIVE: "bg-surface-variant text-on-surface-variant border border-outline-variant",
  APPROVED: "bg-success/10 text-success border border-success/20",
  REJECTED: "bg-critical/20 text-critical border border-critical/30",
  EXECUTED: "bg-primary/20 text-primary border border-primary/30",
};

export function StatusPill({ status }) {
  const cls = STATUS_CLASSES[status] || "bg-surface-variant text-on-surface-variant border border-outline-variant";
  return (
    <span className={`inline-flex items-center gap-1.5 px-2 py-1 rounded font-label-caps text-[10px] uppercase tracking-wider whitespace-nowrap ${cls}`}>
      {["PENDING", "IN_PROGRESS"].includes(status) && <span className="w-1.5 h-1.5 rounded-full bg-current animate-pulse" />}
      {status.replace(/_/g, " ")}
    </span>
  );
}

export function ConfidenceBar({ value }) {
  const pct = Math.round((value ?? 0) * 100);
  const color = pct >= 90 ? "bg-critical" : pct >= 70 ? "bg-high" : pct >= 40 ? "bg-medium" : "bg-low";
  return (
    <div className="flex items-center gap-2 min-w-[120px]">
      <div className="w-full bg-[#131313] rounded-sm h-1.5 overflow-hidden border border-outline-variant/30">
        <div className={`h-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="font-code-sm text-xs text-on-surface-variant">{pct}%</span>
    </div>
  );
}

export function Spinner() {
  return (
    <span className="material-symbols-outlined animate-spin text-primary text-[20px]">progress_activity</span>
  );
}

export function LoadingRow({ label = "Loading..." }) {
  return (
    <div className="flex items-center gap-3 px-6 py-10 text-on-surface-variant text-sm justify-center">
      <Spinner />
      <span>{label}</span>
    </div>
  );
}

export function EmptyState({ glyph = "search_off", title, description }) {
  return (
    <div className="flex flex-col items-center justify-center text-center gap-2 px-6 py-14 text-on-surface-variant">
      <span className="material-symbols-outlined text-[32px] text-on-surface-variant/50 mb-1">{glyph}</span>
      <div className="font-headline-sm text-sm font-semibold text-on-surface">{title}</div>
      {description && <div className="text-xs max-w-sm">{description}</div>}
    </div>
  );
}

export function ErrorBanner({ message }) {
  if (!message) return null;
  return (
    <div className="flex items-start gap-2 bg-error-container/10 border border-error/30 text-error rounded-md px-4 py-3 text-sm mb-4">
      <span className="material-symbols-outlined text-[18px]">warning</span>
      <span>{message}</span>
    </div>
  );
}
