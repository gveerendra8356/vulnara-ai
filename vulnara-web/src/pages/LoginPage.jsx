import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { USE_MOCK } from "../lib/api";

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState(USE_MOCK ? "analyst@vulnara.dev" : "");
  const [password, setPassword] = useState(USE_MOCK ? "demo-password" : "");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      await login(email, password);
      navigate("/");
    } catch (err) {
      setError(err.message || "Login failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="auth-shell">
      <div className="auth-card">
        <div className="panel">
          <div className="panel-pad">
            <div className="brand" style={{ padding: 0, marginBottom: 22 }}>
              <div className="brand-mark">V</div>
              <div>
                <div className="brand-name">Vulnara</div>
                <div className="brand-sub">Analyst Console</div>
              </div>
            </div>

            {USE_MOCK && (
              <div className="warn-box" style={{ marginBottom: 18 }}>
                <span>ⓘ</span>
                <span>
                  Mock Mode is on — sign in with any email/password. Try{" "}
                  <span className="mono">analyst@vulnara.dev</span> or{" "}
                  <span className="mono">admin@vulnara.dev</span> to see the admin nav.
                </span>
              </div>
            )}

            <form onSubmit={handleSubmit}>
              <div className="field">
                <label>Email</label>
                <input
                  className="input"
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@company.com"
                />
              </div>
              <div className="field">
                <label>Password</label>
                <input
                  className="input"
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                />
              </div>
              {error && <div className="text-error">{error}</div>}
              <button className="btn btn-primary" style={{ width: "100%", justifyContent: "center" }} disabled={busy}>
                {busy ? "Signing in..." : "Sign in"}
              </button>
            </form>

            <div className="divider" />
            <div style={{ fontSize: 12.5, color: "var(--text-dim)", textAlign: "center" }}>
              No account? <Link to="/register" className="link-btn">Create one</Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
