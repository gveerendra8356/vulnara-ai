import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { api } from "../lib/api";

export function ResetPasswordPage() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const token = params.get("token") || "";

  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }
    if (password !== confirm) {
      setError("Passwords do not match.");
      return;
    }
    setBusy(true);
    try {
      await api.resetPassword(token, password);
      setDone(true);
    } catch (err) {
      setError(err.message || "This reset link is invalid or has expired.");
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
      </div>

      <div className="z-10 w-full max-w-[420px] px-6">
        <div className="glass-panel rounded-xl p-8 w-full flex flex-col items-center relative overflow-hidden">
          <div className="absolute top-0 left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-primary to-transparent opacity-50" />

          <div className="mb-8 flex flex-col items-center w-full">
            <div className="w-16 h-16 mb-4 rounded-lg bg-primary/10 border border-primary/30 flex items-center justify-center">
              <span className="material-symbols-outlined text-primary text-[32px]">password</span>
            </div>
            <h1 className="font-headline-md text-headline-md text-on-surface tracking-wider uppercase">New Password</h1>
            <p className="font-code-sm text-code-sm text-on-surface-variant mt-2 tracking-widest uppercase text-center">
              Set a new access key
            </p>
          </div>

          {done ? (
            <div className="w-full flex flex-col items-center gap-5 text-center">
              <div className="flex items-start gap-2 bg-success/10 border border-success/30 text-on-surface rounded-md px-4 py-4 text-sm">
                <span className="material-symbols-outlined text-[18px] text-success">check_circle</span>
                <span>Your password has been reset. You can now log in with your new password.</span>
              </div>
              <button
                onClick={() => navigate("/login")}
                className="w-full bg-surface-bright hover:bg-surface-variant text-on-surface font-headline-sm text-headline-sm py-3 rounded border border-outline-variant hover:border-primary transition-all duration-300 flex items-center justify-center gap-2"
              >
                <span className="material-symbols-outlined text-[18px]">login</span>
                Go to Login
              </button>
            </div>
          ) : !token ? (
            <div className="w-full flex flex-col items-center gap-5 text-center">
              <div className="flex items-start gap-2 bg-error/10 border border-error/30 text-on-surface rounded-md px-4 py-4 text-sm">
                <span className="material-symbols-outlined text-[18px] text-error">error</span>
                <span>This reset link is missing its token. Please request a new password reset link.</span>
              </div>
              <button
                onClick={() => navigate("/forgot-password")}
                className="w-full bg-surface-bright hover:bg-surface-variant text-on-surface font-headline-sm text-headline-sm py-3 rounded border border-outline-variant hover:border-primary transition-all duration-300 flex items-center justify-center gap-2"
              >
                <span className="material-symbols-outlined text-[18px]">lock_reset</span>
                Request New Link
              </button>
            </div>
          ) : (
            <form className="w-full flex flex-col gap-5" onSubmit={handleSubmit}>
              <div className="flex flex-col gap-1.5">
                <label className="font-label-caps text-label-caps text-on-surface-variant flex items-center gap-2">
                  <span className="material-symbols-outlined text-[14px]">vpn_key</span>
                  New Password
                </label>
                <input
                  className="w-full bg-primary-container/50 border border-outline-variant rounded py-2.5 px-4 text-on-surface font-code-sm text-code-sm placeholder-on-surface-variant/50 focus:outline-none input-glow transition-all duration-300"
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="At least 8 characters"
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <label className="font-label-caps text-label-caps text-on-surface-variant flex items-center gap-2">
                  <span className="material-symbols-outlined text-[14px]">vpn_key</span>
                  Confirm Password
                </label>
                <input
                  className="w-full bg-primary-container/50 border border-outline-variant rounded py-2.5 px-4 text-on-surface font-code-sm text-code-sm placeholder-on-surface-variant/50 focus:outline-none input-glow transition-all duration-300"
                  type="password"
                  required
                  value={confirm}
                  onChange={(e) => setConfirm(e.target.value)}
                  placeholder="Re-enter new password"
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
                className="mt-2 w-full bg-surface-bright hover:bg-surface-variant text-on-surface font-headline-sm text-headline-sm py-3 rounded border border-outline-variant hover:border-primary transition-all duration-300 flex items-center justify-center gap-2 disabled:opacity-60"
              >
                <span className="material-symbols-outlined text-[18px]">check</span>
                {busy ? "RESETTING..." : "RESET PASSWORD"}
              </button>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
