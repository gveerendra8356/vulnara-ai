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
    <div className="page">
      <div className="page-header">
        <div>
          <h1 className="page-title">New scan</h1>
          <p className="page-subtitle">
            Recon (host discovery, port enumeration, banner grabbing) starts only after you confirm you own this
            target or have explicit written permission to test it. This is enforced server-side, not just in this
            form.
          </p>
        </div>
      </div>

      <form onSubmit={handleSubmit} style={{ maxWidth: 640 }}>
        <div className="panel panel-pad">
          <ErrorBanner message={error} />

          <div className="field">
            <label>Target</label>
            <input
              className="input mono"
              placeholder="e.g. staging.example.com or 10.0.4.22"
              value={target}
              onChange={(e) => setTarget(e.target.value)}
              required
            />
            <div className="hint">Domain or IP address. One target per scan.</div>
          </div>

          <div className="field">
            <label>Authorization justification</label>
            <textarea
              className="input"
              placeholder="e.g. Written pentest authorization from Acme Corp CTO, ref AUTH-2026-014, valid through 2026-09-30."
              value={justification}
              onChange={(e) => setJustification(e.target.value)}
              required
            />
            <div className="hint">
              Logged with a timestamp against your account. Be specific — this record is what proves the scan was
              authorized if it's ever questioned.
            </div>
          </div>

          <div className="checkbox-row" style={{ marginBottom: 16 }}>
            <input
              type="checkbox"
              id="auth-confirm"
              checked={authorized}
              onChange={(e) => setAuthorized(e.target.checked)}
            />
            <label htmlFor="auth-confirm" style={{ cursor: "pointer" }}>
              <div className="ct-title">I own this target, or have explicit written permission to test it</div>
              <div className="ct-desc">
                Required. The scan cannot be created — no nmap process is ever launched — without this confirmed.
              </div>
            </label>
          </div>

          <div className="checkbox-row">
            <input
              type="checkbox"
              id="active-testing"
              checked={activeTesting}
              onChange={(e) => setActiveTesting(e.target.checked)}
            />
            <label htmlFor="active-testing" style={{ cursor: "pointer" }}>
              <div className="ct-title">Enable active testing (SQLi / XSS)</div>
              <div className="ct-desc">
                Opt-in, off by default. Fires a small, rate-limited set of test payloads at discovered forms and
                parameters, and AI-verifies real reflection/execution rather than just pattern-matching. Leave this
                off for a passive recon-only scan.
              </div>
            </label>
          </div>
        </div>

        <div style={{ display: "flex", gap: 10, marginTop: 16 }}>
          <button type="submit" className="btn btn-primary" disabled={mutation.isPending}>
            {mutation.isPending ? "Submitting..." : "Start scan"}
          </button>
          <button type="button" className="btn btn-ghost" onClick={() => navigate(-1)}>
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
}
