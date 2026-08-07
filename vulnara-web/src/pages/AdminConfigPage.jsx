import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";
import { LoadingRow, ErrorBanner } from "../components/Primitives";

export function AdminConfigPage() {
  const qc = useQueryClient();
  const [editing, setEditing] = useState(null);
  const [draft, setDraft] = useState("");
  const [error, setError] = useState("");

  const { data: configs, isLoading } = useQuery({
    queryKey: ["admin-config"],
    queryFn: () => api.listConfig(),
  });

  const updateMutation = useMutation({
    mutationFn: ({ key, value }) => api.updateConfig(key, value),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-config"] });
      setEditing(null);
    },
    onError: (err) => setError(err.message),
  });

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1 className="page-title">Configuration</h1>
          <p className="page-subtitle">
            Runtime-tunable values that steer the AI reasoning layer — e.g. the confidence floor for a finding to
            surface, or the active-testing rate limit. Changes apply immediately, no backend restart required.
          </p>
        </div>
      </div>

      <ErrorBanner message={error} />

      <div className="panel">
        {isLoading ? (
          <LoadingRow label="Loading configuration..." />
        ) : (
          <div className="scroll-x">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Key</th>
                  <th>Value</th>
                  <th>Description</th>
                  <th>Last updated</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {(configs ?? []).map((c) => (
                  <tr key={c.config_key} style={{ cursor: "default" }}>
                    <td className="mono">{c.config_key}</td>
                    <td>
                      {editing === c.config_key ? (
                        <input className="input" style={{ width: 120 }} value={draft} onChange={(e) => setDraft(e.target.value)} autoFocus />
                      ) : (
                        <span className="mono">{c.config_value}</span>
                      )}
                    </td>
                    <td className="small-note" style={{ maxWidth: 320 }}>
                      {c.description}
                    </td>
                    <td className="small-note">{new Date(c.updated_at).toLocaleString()}</td>
                    <td>
                      {editing === c.config_key ? (
                        <div style={{ display: "flex", gap: 6 }}>
                          <button
                            className="btn btn-sm btn-primary"
                            onClick={() => updateMutation.mutate({ key: c.config_key, value: draft })}
                            disabled={updateMutation.isPending}
                          >
                            Save
                          </button>
                          <button className="btn btn-sm btn-ghost" onClick={() => setEditing(null)}>
                            Cancel
                          </button>
                        </div>
                      ) : (
                        <button
                          className="btn btn-sm btn-ghost"
                          onClick={() => {
                            setEditing(c.config_key);
                            setDraft(c.config_value);
                          }}
                        >
                          Edit
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
