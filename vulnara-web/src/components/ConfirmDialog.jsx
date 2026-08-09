export function ConfirmDialog({
  open,
  title,
  body,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  danger = false,
  requireTypedConfirm,
  typedValue,
  onTypedChange,
  onConfirm,
  onCancel,
  confirmDisabled,
}) {
  if (!open) return null;
  return (
    <div
      className="fixed inset-0 z-[100] bg-black/70 backdrop-blur-sm flex items-center justify-center p-4"
      onClick={onCancel}
    >
      <div
        className="glass-panel rounded-xl w-full max-w-md overflow-hidden"
        style={{ background: "rgba(18, 33, 49, 0.95)" }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center gap-3 px-6 py-4 border-b border-outline-variant">
          <span className={`material-symbols-outlined ${danger ? "text-error" : "text-primary"}`}>
            {danger ? "warning" : "check_circle"}
          </span>
          <strong className="font-headline-sm text-headline-sm text-on-surface">{title}</strong>
        </div>
        <div className="px-6 py-5 text-sm text-on-surface-variant leading-relaxed">
          {body}
          {requireTypedConfirm && (
            <div className="mt-4">
              <label className="block font-label-caps text-[10px] text-on-surface-variant/70 uppercase mb-2">
                Type <span className="font-code-sm text-primary">{requireTypedConfirm}</span> to confirm
              </label>
              <input
                className="w-full bg-[#131313] border border-outline-variant rounded-md py-2 px-3 text-on-surface font-code-sm text-sm focus:outline-none focus:border-primary/50"
                value={typedValue}
                onChange={(e) => onTypedChange(e.target.value)}
                placeholder={requireTypedConfirm}
              />
            </div>
          )}
        </div>
        <div className="flex justify-end gap-3 px-6 py-4 border-t border-outline-variant bg-surface-container-low/50">
          <button
            className="px-4 py-2 rounded-md text-sm font-medium text-on-surface-variant hover:bg-surface-variant/50 transition-colors"
            onClick={onCancel}
          >
            {cancelLabel}
          </button>
          <button
            className={`px-4 py-2 rounded-md text-sm font-bold transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${
              danger
                ? "bg-error text-on-error hover:bg-error/90"
                : "bg-primary text-on-primary hover:bg-primary/90"
            }`}
            onClick={onConfirm}
            disabled={confirmDisabled}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
