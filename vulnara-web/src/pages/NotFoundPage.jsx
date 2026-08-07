import { Link } from "react-router-dom";

export function NotFoundPage() {
  return (
    <div className="auth-shell">
      <div style={{ textAlign: "center" }}>
        <div className="mono" style={{ fontSize: 42, fontWeight: 700, color: "var(--accent-strong)" }}>
          404
        </div>
        <p style={{ color: "var(--text-dim)", marginBottom: 18 }}>That page doesn't exist.</p>
        <Link to="/" className="btn btn-primary">
          Back to dashboard
        </Link>
      </div>
    </div>
  );
}
