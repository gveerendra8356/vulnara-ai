import { useState } from "react";
import { useNavigate } from "react-router-dom";
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
    <div className="bg-background text-on-background min-h-screen flex items-center justify-center font-body-md relative overflow-hidden">
      {/* Atmospheric Background */}
      <div className="absolute inset-0 z-0">
        <div className="absolute inset-0 bg-surface" />
        <div className="absolute inset-0 cyber-grid" />
        <div className="absolute inset-0 bg-gradient-to-t from-background via-transparent to-transparent" />
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-primary-container rounded-full blur-[120px] opacity-30 mix-blend-screen" />
        <div className="absolute bottom-1/4 right-1/4 w-64 h-64 bg-surface-container-high rounded-full blur-[90px] opacity-40 mix-blend-screen" />
      </div>

      <div className="z-10 w-full max-w-[420px] px-6">
        <div className="glass-panel rounded-xl p-8 w-full flex flex-col items-center relative overflow-hidden">
          <div className="absolute top-0 left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-primary to-transparent opacity-50" />

          <div className="mb-8 flex flex-col items-center w-full">
            <img src="/logo.png" alt="Vulnara Logo" className="h-20 object-contain mb-4" />
            <h1 className="font-headline-md text-headline-md text-on-surface tracking-wider uppercase">Terminal Access</h1>
            <p className="font-code-sm text-code-sm text-on-surface-variant mt-2 tracking-widest uppercase">
              Vulnara Analyst Console
            </p>
          </div>

          <div className="w-full flex border-b border-outline-variant mb-6 relative">
            <button
              type="button"
              className="flex-1 py-3 text-primary font-code-sm text-code-sm uppercase tracking-widest border-b-2 border-primary relative z-10"
            >
              Login
            </button>
            <button
              type="button"
              onClick={() => navigate("/register")}
              className="flex-1 py-3 text-on-surface-variant font-code-sm text-code-sm uppercase tracking-widest hover:text-primary transition-colors"
            >
              Register
            </button>
          </div>

          {USE_MOCK && (
            <div className="w-full flex items-start gap-2 bg-primary/5 border border-primary/20 text-on-surface-variant rounded-md px-4 py-3 text-xs mb-5">
              <span className="material-symbols-outlined text-[16px] text-primary">info</span>
              <span>
                Mock Mode is on — sign in with any email/password. Try{" "}
                <span className="font-code-sm text-primary">analyst@vulnara.dev</span> or{" "}
                <span className="font-code-sm text-primary">admin@vulnara.dev</span> to see the admin nav.
              </span>
            </div>
          )}

          <form className="w-full flex flex-col gap-5" onSubmit={handleSubmit}>
            <div className="flex flex-col gap-1.5">
              <label className="font-label-caps text-label-caps text-on-surface-variant flex items-center gap-2">
                <span className="material-symbols-outlined text-[14px]">badge</span>
                Operator Email
              </label>
              <input
                className="w-full bg-primary-container/50 border border-outline-variant rounded py-2.5 px-4 text-on-surface font-code-sm text-code-sm placeholder-on-surface-variant/50 focus:outline-none input-glow transition-all duration-300"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@company.com"
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="font-label-caps text-label-caps text-on-surface-variant flex items-center gap-2">
                <span className="material-symbols-outlined text-[14px]">vpn_key</span>
                Access Key
              </label>
              <input
                className="w-full bg-primary-container/50 border border-outline-variant rounded py-2.5 px-4 text-on-surface font-code-sm text-code-sm placeholder-on-surface-variant/50 focus:outline-none input-glow transition-all duration-300"
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
              />
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
              <span className="material-symbols-outlined text-[18px]">login</span>
              {busy ? "SIGNING IN..." : "INITIALIZE LINK"}
            </button>
          </form>

          <div className="w-full mt-8 pt-4 border-t border-outline-variant/30 flex justify-between items-center">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-primary animate-pulse" />
              <span className="font-code-sm text-code-sm text-on-surface-variant uppercase">Sys Status: Optimal</span>
            </div>
            <span className="font-code-sm text-code-sm text-on-surface-variant opacity-50">v1.0.2</span>
          </div>
        </div>
      </div>
    </div>
  );
}
