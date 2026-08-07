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
    <div className="modal-backdrop" onClick={onCancel}>
      <div className="modal-card" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <span style={{ fontSize: 18 }}>{danger ? "⚠️" : "✅"}</span>
          <strong>{title}</strong>
        </div>
        <div className="modal-body">
          {body}
          {requireTypedConfirm && (
            <div style={{ marginTop: 14 }}>
              <label style={{ fontSize: 12, color: "var(--text-faint)", display: "block", marginBottom: 6 }}>
                Type <span className="mono">{requireTypedConfirm}</span> to confirm
              </label>
              <input
                className="input"
                value={typedValue}
                onChange={(e) => onTypedChange(e.target.value)}
                placeholder={requireTypedConfirm}
              />
            </div>
          )}
        </div>
        <div className="modal-footer">
          <button className="btn btn-ghost" onClick={onCancel}>
            {cancelLabel}
          </button>
          <button
            className={danger ? "btn btn-danger" : "btn btn-primary"}
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
