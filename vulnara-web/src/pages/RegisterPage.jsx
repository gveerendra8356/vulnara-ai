import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export function RegisterPage() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ full_name: "", email: "", password: "", role: "client" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const update = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      await register(form);
      navigate("/login");
    } catch (err) {
      setError(err.message || "Registration failed");
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
                <div className="brand-sub">Create account</div>
              </div>
            </div>

            <form onSubmit={handleSubmit}>
              <div className="field">
                <label>Full name</label>
                <input className="input" required value={form.full_name} onChange={update("full_name")} />
              </div>
              <div className="field">
                <label>Email</label>
                <input className="input" type="email" required value={form.email} onChange={update("email")} />
              </div>
              <div className="field">
                <label>Password</label>
                <input className="input" type="password" required value={form.password} onChange={update("password")} />
              </div>
              <div className="field">
                <label>Role</label>
                <select className="select" value={form.role} onChange={update("role")}>
                  <option value="client">Client — view findings & approve on mobile</option>
                  <option value="analyst">Analyst — run scans & review remediation</option>
                </select>
                <div className="hint">Admin accounts are created by an existing admin, not via self-signup.</div>
              </div>
              {error && <div className="text-error">{error}</div>}
              <button className="btn btn-primary" style={{ width: "100%", justifyContent: "center" }} disabled={busy}>
                {busy ? "Creating account..." : "Create account"}
              </button>
            </form>

            <div className="divider" />
            <div style={{ fontSize: 12.5, color: "var(--text-dim)", textAlign: "center" }}>
              Already have an account? <Link to="/login" className="link-btn">Sign in</Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
