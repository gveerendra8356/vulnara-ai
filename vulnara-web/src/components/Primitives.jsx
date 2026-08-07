export function SeverityBadge({ severity }) {
  return (
    <span className={`badge badge-${severity}`}>
      <span className="badge-dot" />
      {severity}
    </span>
  );
}

export function StatusPill({ status }) {
  return <span className={`status-pill ${status}`}>{status.replace("_", " ")}</span>;
}

export function ConfidenceBar({ value }) {
  const pct = Math.round((value ?? 0) * 100);
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
      <div className="confidence-bar">
        <div className="confidence-bar-fill" style={{ width: `${pct}%` }} />
      </div>
      <span className="mono small-note">{pct}%</span>
    </div>
  );
}

export function Spinner() {
  return <div className="spinner" />;
}

export function LoadingRow({ label = "Loading..." }) {
  return (
    <div className="loading-row">
      <Spinner />
      <span>{label}</span>
    </div>
  );
}

export function EmptyState({ glyph = "∅", title, description }) {
  return (
    <div className="empty-state">
      <div className="glyph">{glyph}</div>
      <div style={{ fontWeight: 700, color: "var(--text-dim)", marginBottom: 4 }}>{title}</div>
      {description && <div style={{ fontSize: 12.5 }}>{description}</div>}
    </div>
  );
}

export function ErrorBanner({ message }) {
  if (!message) return null;
  return (
    <div className="warn-box" style={{ marginBottom: 16 }}>
      <span>⚠</span>
      <span>{message}</span>
    </div>
  );
}
