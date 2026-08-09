import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "../context/AuthContext";
import { api } from "../lib/api";
import { StatusPill, LoadingRow, ErrorBanner } from "../components/Primitives";
import { ConfirmDialog } from "../components/ConfirmDialog";

export function RemediationReviewPage() {
  const { remediationId } = useParams();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const { user } = useAuth();
  const isClient = user?.role === "client";
  const isAnalystOrAdmin = user?.role === "analyst" || user?.role === "admin";

  const [rejectOpen, setRejectOpen] = useState(false);
  const [rejectReason, setRejectReason] = useState("");
  const [executeOpen, setExecuteOpen] = useState(false);
  const [executeTyped, setExecuteTyped] = useState("");
  const [error, setError] = useState("");
  const [copyLabel, setCopyLabel] = useState("Copy script");

  const { data: rem, isLoading } = useQuery({
    queryKey: ["remediation", remediationId],
    queryFn: () => api.getRemediation(remediationId),
  });

  const invalidate = () => qc.invalidateQueries({ queryKey: ["remediation", remediationId] });

  const approveMutation = useMutation({
    mutationFn: () => api.approveRemediation(remediationId),
    onSuccess: invalidate,
    onError: (err) => setError(err.message),
  });

  const rejectMutation = useMutation({
    mutationFn: () => api.rejectRemediation(remediationId, rejectReason),
    onSuccess: () => {
      invalidate();
      setRejectOpen(false);
    },
    onError: (err) => setError(err.message),
  });

  const executeMutation = useMutation({
    mutationFn: () => api.markExecuted(remediationId),
    onSuccess: () => {
      invalidate();
      setExecuteOpen(false);
      setExecuteTyped("");
    },
    onError: (err) => setError(err.message),
  });

  if (isLoading || !rem) {
    return (
      <div className="p-container-padding">
        <LoadingRow label="Loading remediation..." />
      </div>
    );
  }

  const copyScript = async () => {
    try {
      await navigator.clipboard.writeText(rem.technical_script);
      setCopyLabel("Copied ✓");
      setTimeout(() => setCopyLabel("Copy script"), 1500);
    } catch {
      setCopyLabel("Copy failed");
    }
  };

  return (
    <div className="flex flex-col min-h-full">
      {/* Top App Bar */}
      <header className="bg-surface/60 backdrop-blur-xl border-b border-outline-variant flex items-center justify-between h-16 px-6 sticky top-0 z-30">
        <div className="flex items-center gap-4 min-w-0">
          <button
            onClick={() => navigate(-1)}
            className="w-8 h-8 flex items-center justify-center rounded-full hover:bg-surface-variant transition-colors text-on-surface-variant hover:text-primary shrink-0"
          >
            <span className="material-symbols-outlined text-[20px]">arrow_back</span>
          </button>
          <h2 className="font-headline-sm text-headline-sm text-on-surface font-code-sm truncate">{rem.remediation_id}</h2>
          <StatusPill status={rem.status} />
        </div>
      </header>

      <main className="flex-1 overflow-hidden p-6 flex flex-col lg:flex-row gap-6 pb-28">
        {/* Left Pane: Executive Summary */}
        <div className="lg:w-1/3 flex flex-col gap-6 overflow-y-auto pr-2">
          <div className="glass-panel rounded-xl p-6 flex flex-col gap-4">
            <div className="flex justify-between items-center">
              <h3 className="font-headline-sm text-headline-sm text-on-surface">AI Confidence</h3>
              <span className="material-symbols-outlined text-success">verified_user</span>
            </div>
            <div className="flex items-end gap-3">
              <span className="font-display-lg text-display-lg text-success">{Math.round(rem.ai_confidence * 100)}%</span>
              <span className="font-body-md text-body-md text-on-surface-variant pb-2">High certainty for success</span>
            </div>
            <div className="w-full bg-surface-container-highest rounded-full h-2 mt-1">
              <div className="bg-success h-2 rounded-full" style={{ width: `${Math.round(rem.ai_confidence * 100)}%` }} />
            </div>
          </div>

          <div className="glass-panel rounded-xl p-6 flex flex-col gap-4">
            <h3 className="font-headline-sm text-headline-sm text-on-surface mb-2">Context</h3>
            <div className="flex flex-col gap-3">
              <div className="flex justify-between border-b border-outline-variant pb-2">
                <span className="font-body-md text-body-md text-on-surface-variant">Finding</span>
                <span className="font-code-sm text-code-sm text-on-surface">{rem.vuln_id}</span>
              </div>
              <div className="flex justify-between border-b border-outline-variant pb-2">
                <span className="font-body-md text-body-md text-on-surface-variant">Target OS</span>
                <span className="font-code-sm text-code-sm text-on-surface bg-surface-container-highest px-2 py-1 rounded">
                  {rem.target_os || "unspecified"}
                </span>
              </div>
              <div className="flex justify-between border-b border-outline-variant pb-2">
                <span className="font-body-md text-body-md text-on-surface-variant">Status</span>
                <StatusPill status={rem.status} />
              </div>
            </div>
          </div>

          <div className="glass-panel rounded-xl p-6 flex flex-col gap-4">
            <h3 className="font-headline-sm text-headline-sm text-on-surface mb-2 flex items-center gap-2">
              <span className="material-symbols-outlined text-primary">summarize</span>
              Executive Summary
            </h3>
            <p className="font-body-md text-body-md text-on-surface-variant leading-relaxed">{rem.executive_summary}</p>
          </div>
        </div>

        {/* Right Pane: Code */}
        <div className="lg:w-2/3 glass-panel rounded-xl flex flex-col overflow-hidden relative">
          <div className="bg-surface-container-high border-b border-outline-variant px-4 py-3 flex justify-between items-center">
            <div className="flex items-center gap-2">
              <span className="material-symbols-outlined text-on-surface-variant text-sm">code</span>
              <span className="font-code-sm text-code-sm text-on-surface">Technical script</span>
            </div>
            <button
              onClick={copyScript}
              className="px-3 py-1 rounded text-xs font-medium bg-surface-variant text-on-surface hover:bg-surface-container-highest transition-colors"
            >
              {copyLabel}
            </button>
          </div>
          <div className="flex-1 bg-[#0a0a0a] overflow-auto p-4 font-code-sm text-code-sm">
            <pre className="text-[#a0a0a0] whitespace-pre-wrap break-words">{rem.technical_script}</pre>
          </div>
        </div>
      </main>

      {/* Review decision */}
      <div className="glass-overlay border-t border-outline-variant p-4 flex flex-col gap-3 fixed bottom-0 right-0 left-0 md:left-[260px] z-40">
        <div className="max-w-5xl w-full mx-auto lg:mx-0">
          <ErrorBanner message={error} />

          {rem.status === "PENDING" && isAnalystOrAdmin && (
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <p className="text-xs text-on-surface-variant max-w-xl flex items-center gap-2">
                <span className="material-symbols-outlined text-[16px] text-medium">warning</span>
                This script was generated by AI and has not run anywhere yet. Approval doesn't execute it, but it
                does authorize a human operator to.
              </p>
              <div className="flex gap-3 shrink-0">
                <button
                  onClick={() => setRejectOpen(true)}
                  className="px-6 py-2 rounded-lg font-headline-sm text-sm font-semibold border border-error/50 text-error hover:bg-error/10 transition-colors flex items-center gap-2"
                >
                  <span className="material-symbols-outlined text-[18px]">refresh</span>
                  Reject
                </button>
                <button
                  onClick={() => approveMutation.mutate()}
                  disabled={approveMutation.isPending}
                  className="px-6 py-2 rounded-lg font-headline-sm text-sm font-semibold bg-success hover:bg-success/90 text-white transition-colors shadow-[0_0_15px_rgba(16,185,129,0.3)] flex items-center gap-2 disabled:opacity-60"
                >
                  <span className="material-symbols-outlined text-[18px]">check_circle</span>
                  {approveMutation.isPending ? "Approving..." : "Approve Script"}
                </button>
              </div>
            </div>
          )}

          {rem.status === "PENDING" && isClient && (
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <p className="text-xs text-on-surface-variant max-w-xl">
                This remediation is currently pending review by an analyst. Check back later once it has been approved.
              </p>
            </div>
          )}

          {rem.status === "APPROVED" && (
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <p className="text-xs text-on-surface-variant max-w-xl">
                Approved by <span className="font-code-sm text-on-surface">{rem.reviewed_by}</span> on{" "}
                {rem.reviewed_at ? new Date(rem.reviewed_at).toLocaleString() : "—"}. Execution happens out-of-band —
                use the button below only once that has actually happened, to record it.
              </p>
              {isClient && (
                <button
                  onClick={() => setExecuteOpen(true)}
                  className="px-6 py-2 rounded-lg font-headline-sm text-sm font-semibold bg-primary text-on-primary hover:bg-primary/90 transition-colors flex items-center gap-2 shrink-0"
                >
                  <span className="material-symbols-outlined text-[18px]">task_alt</span>
                  Mark as executed
                </button>
              )}
            </div>
          )}

          {rem.status === "REJECTED" && (
            <p className="text-xs text-on-surface-variant">
              Rejected by <span className="font-code-sm text-on-surface">{rem.reviewed_by}</span> on{" "}
              {rem.reviewed_at ? new Date(rem.reviewed_at).toLocaleString() : "—"}
              {rem.reject_reason ? `: "${rem.reject_reason}"` : "."} Generate a new remediation from the finding page
              if you'd like the AI to try again.
            </p>
          )}

          {rem.status === "EXECUTED" && (
            <p className="text-xs text-on-surface-variant">
              Marked executed on {rem.executed_at ? new Date(rem.executed_at).toLocaleString() : "—"}. This
              remediation's lifecycle is complete.
            </p>
          )}
        </div>
      </div>

      <ConfirmDialog
        open={rejectOpen}
        title="Reject this remediation?"
        body={
          <div>
            <label className="block text-xs text-on-surface-variant mb-2">Reason (optional)</label>
            <textarea
              className="w-full bg-[#131313] border border-outline-variant rounded-md py-2 px-3 text-on-surface text-sm focus:outline-none focus:border-primary/50"
              rows={3}
              value={rejectReason}
              onChange={(e) => setRejectReason(e.target.value)}
              placeholder="e.g. Script needs a rollback step before it's safe to run."
            />
          </div>
        }
        confirmLabel={rejectMutation.isPending ? "Rejecting..." : "Reject"}
        danger
        onConfirm={() => rejectMutation.mutate()}
        onCancel={() => setRejectOpen(false)}
        confirmDisabled={rejectMutation.isPending}
      />

      <ConfirmDialog
        open={executeOpen}
        title="Confirm execution record"
        body="This records that the approved script has already been run against the target by your ops team. It does not run anything itself — but the EXECUTED status is treated as ground truth elsewhere in the app, so only confirm this once it's actually true."
        requireTypedConfirm="EXECUTED"
        typedValue={executeTyped}
        onTypedChange={setExecuteTyped}
        confirmLabel={executeMutation.isPending ? "Saving..." : "Mark as executed"}
        danger
        confirmDisabled={executeTyped !== "EXECUTED" || executeMutation.isPending}
        onConfirm={() => executeMutation.mutate()}
        onCancel={() => {
          setExecuteOpen(false);
          setExecuteTyped("");
        }}
      />
    </div>
  );
}
