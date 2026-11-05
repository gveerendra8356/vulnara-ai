import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../lib/api";

export function ForgotPasswordPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      await api.forgotPassword(email);
      // Always show the same confirmation — we never reveal whether the email
      // is registered.
      setSent(true);
    } catch (err) {
      setError(err.message || "Something went wrong. Please try again.");
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
              <span className="material-symbols-outlined text-primary text-[32px]">lock_reset</span>
            </div>
            <h1 className="font-headline-md text-headline-md text-on-surface tracking-wider uppercase">Reset Access</h1>
            <p className="font-code-sm text-code-sm text-on-surface-variant mt-2 tracking-widest uppercase text-center">
              Recover your account
            </p>
          </div>

          {sent ? (
            <div className="w-full flex flex-col items-center gap-5 text-center">
              <div className="flex items-start gap-2 bg-success/10 border border-success/30 text-on-surface rounded-md px-4 py-4 text-sm">
                <span className="material-symbols-outlined text-[18px] text-success">mark_email_read</span>
                <span>
                  If an account exists for <span className="font-code-sm text-primary">{email}</span>, a password
                  reset link has been sent. Check your inbox (and spam) — the link expires in 30 minutes.
                </span>
              </div>
              <button
                onClick={() => navigate("/login")}
                className="w-full bg-surface-bright hover:bg-surface-variant text-on-surface font-headline-sm text-headline-sm py-3 rounded border border-outline-variant hover:border-primary transition-all duration-300 flex items-center justify-center gap-2"
              >
                <span className="material-symbols-outlined text-[18px]">arrow_back</span>
                Back to Login
              </button>
            </div>
          ) : (
            <form className="w-full flex flex-col gap-5" onSubmit={handleSubmit}>
              <p className="text-xs text-on-surface-variant text-center -mt-2">
                Enter your registered email and we'll send you a link to reset your password.
              </p>
              <div className="flex flex-col gap-1.5">
                <label className="font-label-caps text-label-caps text-on-surface-variant flex items-center gap-2">
                  <span className="material-symbols-outlined text-[14px]">badge</span>
                  Registered Email
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
                <span className="material-symbols-outlined text-[18px]">send</span>
                {busy ? "SENDING..." : "SEND RESET LINK"}
              </button>

              <button
                type="button"
                onClick={() => navigate("/login")}
                className="text-xs text-on-surface-variant hover:text-primary transition-colors"
              >
                &larr; Back to login
              </button>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
