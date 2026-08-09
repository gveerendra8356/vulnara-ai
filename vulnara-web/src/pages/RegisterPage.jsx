import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export function RegisterPage() {
  const { register, login } = useAuth();
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
      await login({ email: form.email, password: form.password });
      navigate("/");
    } catch (err) {
      setError(err.message || "Registration failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="bg-background text-on-background min-h-screen flex items-center justify-center font-body-md relative overflow-hidden">
      <div className="absolute inset-0 z-0">
        <div className="absolute inset-0 bg-surface" />
        <div className="absolute inset-0 cyber-grid" />
        <div className="absolute inset-0 bg-gradient-to-t from-background via-transparent to-transparent" />
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-primary-container rounded-full blur-[120px] opacity-30 mix-blend-screen" />
        <div className="absolute bottom-1/4 right-1/4 w-64 h-64 bg-surface-container-high rounded-full blur-[90px] opacity-40 mix-blend-screen" />
      </div>

      <div className="z-10 w-full max-w-[440px] px-6">
        <div className="glass-panel rounded-xl p-8 w-full flex flex-col items-center relative overflow-hidden">
          <div className="absolute top-0 left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-primary to-transparent opacity-50" />

          <div className="mb-8 flex flex-col items-center w-full">
            <div className="w-16 h-16 mb-4 rounded-lg bg-primary/10 border border-primary/30 flex items-center justify-center shadow-[0_0_15px_rgba(200,198,197,0.2)]">
              <span className="material-symbols-outlined text-primary text-[32px]" style={{ fontVariationSettings: "'FILL' 1" }}>
                security
              </span>
            </div>
            <h1 className="font-headline-md text-headline-md text-on-surface tracking-wider uppercase">New Operator</h1>
            <p className="font-code-sm text-code-sm text-on-surface-variant mt-2 tracking-widest uppercase">Create account</p>
          </div>

          <div className="w-full flex border-b border-outline-variant mb-6 relative">
            <button
              type="button"
              onClick={() => navigate("/login")}
              className="flex-1 py-3 text-on-surface-variant font-code-sm text-code-sm uppercase tracking-widest hover:text-primary transition-colors"
            >
              Login
            </button>
            <button
              type="button"
              className="flex-1 py-3 text-primary font-code-sm text-code-sm uppercase tracking-widest border-b-2 border-primary relative z-10"
            >
              Register
            </button>
          </div>

          <form className="w-full flex flex-col gap-5" onSubmit={handleSubmit}>
            <div className="flex flex-col gap-1.5">
              <label className="font-label-caps text-label-caps text-on-surface-variant flex items-center gap-2">
                <span className="material-symbols-outlined text-[14px]">person</span>
                Full name
              </label>
              <input
                className="w-full bg-primary-container/50 border border-outline-variant rounded py-2.5 px-4 text-on-surface font-code-sm text-code-sm placeholder-on-surface-variant/50 focus:outline-none input-glow transition-all duration-300"
                required
                value={form.full_name}
                onChange={update("full_name")}
                placeholder="Jane Operator"
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="font-label-caps text-label-caps text-on-surface-variant flex items-center gap-2">
                <span className="material-symbols-outlined text-[14px]">badge</span>
                Email
              </label>
              <input
                className="w-full bg-primary-container/50 border border-outline-variant rounded py-2.5 px-4 text-on-surface font-code-sm text-code-sm placeholder-on-surface-variant/50 focus:outline-none input-glow transition-all duration-300"
                type="email"
                required
                value={form.email}
                onChange={update("email")}
                placeholder="you@company.com"
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="font-label-caps text-label-caps text-on-surface-variant flex items-center gap-2">
                <span className="material-symbols-outlined text-[14px]">vpn_key</span>
                Password
              </label>
              <input
                className="w-full bg-primary-container/50 border border-outline-variant rounded py-2.5 px-4 text-on-surface font-code-sm text-code-sm placeholder-on-surface-variant/50 focus:outline-none input-glow transition-all duration-300"
                type="password"
                required
                value={form.password}
                onChange={update("password")}
                placeholder="••••••••••••"
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="font-label-caps text-label-caps text-on-surface-variant flex items-center gap-2">
                <span className="material-symbols-outlined text-[14px]">shield_person</span>
                Role
              </label>
              <select
                className="w-full bg-primary-container/50 border border-outline-variant rounded py-2.5 px-4 text-on-surface text-sm focus:outline-none input-glow transition-all duration-300 appearance-none cursor-pointer"
                value={form.role}
                onChange={update("role")}
              >
                <option value="client">Client — view findings &amp; approve on mobile</option>
                <option value="analyst">Analyst — run scans &amp; review remediation</option>
              </select>
              <div className="text-[11px] text-on-surface-variant/70 mt-1">
                Admin accounts are created by an existing admin, not via self-signup.
              </div>
            </div>

            {error && (
              <div className="flex items-center gap-2 text-error text-sm">
                <span className="material-symbols-outlined text-[16px]">error</span>
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={busy}
              className="mt-2 w-full bg-surface-bright hover:bg-surface-variant text-on-surface font-headline-sm text-headline-sm py-3 rounded border border-outline-variant hover:border-primary transition-all duration-300 flex items-center justify-center gap-2 group relative overflow-hidden disabled:opacity-60"
            >
              <div className="absolute inset-0 bg-gradient-to-r from-transparent via-primary/5 to-transparent -translate-x-full group-hover:translate-x-full transition-transform duration-700 ease-in-out" />
              <span className="material-symbols-outlined text-[18px]">person_add</span>
              {busy ? "CREATING..." : "CREATE ACCOUNT"}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
