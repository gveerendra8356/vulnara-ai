import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import { api } from "../lib/api";
import { ErrorBanner } from "../components/Primitives";

export function NewScanPage() {
  const navigate = useNavigate();
  const [target, setTarget] = useState("");
  const [justification, setJustification] = useState("");
  const [authorized, setAuthorized] = useState(false);
  const [activeTesting, setActiveTesting] = useState(false);
  const [error, setError] = useState("");

  const mutation = useMutation({
    mutationFn: () =>
      api.createScan({
        target,
        authorization_confirmed: authorized,
        authorization_justification: justification,
        active_testing_enabled: activeTesting,
      }),
    onSuccess: (scan) => navigate(`/scans/${scan.scan_id}`),
    onError: (err) => setError(err.message),
  });

  const canSubmit = target.trim().length > 0 && authorized && justification.trim().length >= 10;

  const handleSubmit = (e) => {
    e.preventDefault();
    setError("");
    if (!canSubmit) {
      setError("Confirm authorization and provide a justification of at least 10 characters before scanning.");
      return;
    }
    mutation.mutate();
  };

  return (
    <div className="p-container-padding bg-[radial-gradient(ellipse_at_top_right,rgba(13,28,45,0.6),transparent_60%)]">
      <div className="max-w-4xl mx-auto">
        <div className="mb-8">
          <button
            type="button"
            onClick={() => navigate(-1)}
            className="flex items-center gap-2 text-on-surface-variant mb-2 hover:text-primary transition-colors"
          >
            <span className="material-symbols-outlined text-sm">arrow_back</span>
            <span className="text-sm font-medium">Back to Scans</span>
          </button>
          <h2 className="font-display-lg text-display-lg text-on-surface">New Scan Configurator</h2>
          <p className="font-body-md text-on-surface-variant mt-2 max-w-2xl">
            Recon (host discovery, port enumeration, banner grabbing) starts only after you confirm you own this
            target or have explicit written permission to test it. This is enforced server-side, not just in this
            form.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          <ErrorBanner message={error} />

          {/* Target Configuration */}
          <div className="glass-panel rounded-xl p-6">
            <h3 className="font-headline-sm text-headline-sm text-on-surface mb-4 flex items-center gap-2">
              <span className="material-symbols-outlined text-primary">target</span> Target Configuration
            </h3>
            <div className="space-y-4">
              <div>
                <label className="block font-label-caps text-label-caps text-on-surface-variant mb-2 uppercase">
                  Target IP / Hostname
                </label>
                <input
                  className="w-full bg-[#131313] border border-outline-variant rounded-md px-4 py-3 text-on-surface font-code-sm text-code-sm focus:outline-none focus:border-primary transition-colors placeholder:text-on-surface-variant/50"
                  placeholder="e.g. staging.example.com or 10.0.4.22"
                  value={target}
                  onChange={(e) => setTarget(e.target.value)}
                  required
                />
                <div className="text-[11px] text-on-surface-variant/70 mt-1.5">Domain or IP address. One target per scan.</div>
              </div>

              <div>
                <label className="flex items-center justify-between p-4 bg-surface-variant/30 rounded-lg border border-outline-variant/50 cursor-pointer">
                  <div>
                    <h4 className="font-medium text-on-surface">Active AI Testing</h4>
                    <p className="text-xs text-on-surface-variant mt-1 max-w-md">
                      Opt-in, off by default. Fires a small, rate-limited set of SQLi/XSS payloads at discovered
                      forms and parameters, and AI-verifies real reflection/execution rather than just
                      pattern-matching. Leave off for a passive recon-only scan.
                    </p>
                  </div>
                  <span className="relative inline-flex items-center shrink-0 ml-4">
                    <input
                      type="checkbox"
                      className="sr-only peer"
                      checked={activeTesting}
                      onChange={(e) => setActiveTesting(e.target.checked)}
                    />
                    <span className="w-11 h-6 bg-surface-container-highest peer-focus:ring-2 peer-focus:ring-primary rounded-full peer peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-secondary after:border after:border-secondary after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary peer-checked:after:bg-surface" />
                  </span>
                </label>
              </div>
            </div>
          </div>

          {/* Authorization Gate */}
          <div className="bg-error-container/10 border border-error/30 rounded-xl p-6 relative overflow-hidden">
            <div className="absolute top-0 left-0 w-1 h-full bg-error" />
            <h3 className="font-headline-sm text-headline-sm text-error mb-2 flex items-center gap-2">
              <span className="material-symbols-outlined text-error">gavel</span> Authorization Gate
            </h3>
            <p className="text-sm text-on-surface-variant mb-4">
              You are initiating a potentially disruptive operation. Explicit authorization and justification are
              required for auditing purposes — logged with a timestamp against your account.
            </p>
            <div className="space-y-4">
              <div>
                <label className="block font-label-caps text-label-caps text-error/80 mb-2 uppercase">
                  Authorization justification
                </label>
                <textarea
                  className="w-full bg-[#131313] border border-error/30 rounded-md px-4 py-3 text-on-surface focus:outline-none focus:border-error transition-colors placeholder:text-error/30"
                  placeholder="e.g. Written pentest authorization from Acme Corp CTO, ref AUTH-2026-014, valid through 2026-09-30."
                  rows={3}
                  value={justification}
                  onChange={(e) => setJustification(e.target.value)}
                  required
                />
              </div>
              <label className="flex items-start gap-3 cursor-pointer group">
                <div className="flex-shrink-0 mt-0.5">
                  <input
                    type="checkbox"
                    className="w-5 h-5 rounded bg-[#131313] border-error/50 text-error focus:ring-error"
                    checked={authorized}
                    onChange={(e) => setAuthorized(e.target.checked)}
                  />
                </div>
                <span className="text-sm text-on-surface-variant group-hover:text-on-surface transition-colors">
                  I own this target, or have explicit written permission to test it. The scan cannot be created — no
                  process is ever launched — without this confirmed.
                </span>
              </label>
            </div>
          </div>

          {/* Actions */}
          <div className="flex items-center justify-end gap-4 pt-4 border-t border-outline-variant">
            <button
              type="button"
              onClick={() => navigate(-1)}
              className="px-6 py-2.5 rounded-md text-sm font-medium text-on-surface-variant hover:text-on-surface hover:bg-surface-variant/50 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={mutation.isPending}
              className="px-6 py-2.5 rounded-md text-sm font-bold bg-primary text-surface hover:bg-primary-fixed transition-colors shadow-[0_0_10px_rgba(200,198,197,0.3)] flex items-center gap-2 disabled:opacity-60"
            >
              <span className="material-symbols-outlined text-sm font-bold">play_arrow</span>
              {mutation.isPending ? "Submitting..." : "Initialize Scan"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
