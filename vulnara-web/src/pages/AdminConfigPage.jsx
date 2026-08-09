import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";
import { LoadingRow, ErrorBanner, EmptyState } from "../components/Primitives";

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

  const items = configs ?? [];

  return (
    <div className="p-container-padding max-w-6xl mx-auto flex flex-col gap-6">
      <div>
        <h2 className="font-display-lg text-display-lg text-on-surface flex items-center gap-3">
          <span className="material-symbols-outlined text-primary text-[32px]">tune</span>
          Configuration
        </h2>
        <p className="text-on-surface-variant mt-2 font-body-md max-w-2xl">
          Runtime-tunable values that steer the AI reasoning layer — e.g. the confidence floor for a finding to
          surface, or the active-testing rate limit. Changes apply immediately, no backend restart required.
        </p>
      </div>

      <ErrorBanner message={error} />

      <div className="glass-panel rounded-xl overflow-hidden">
        {isLoading ? (
          <LoadingRow label="Loading configuration..." />
        ) : items.length === 0 ? (
          <EmptyState glyph="tune" title="No config values yet" />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse min-w-[800px]">
              <thead className="bg-surface-container-low/50 border-b border-outline-variant">
                <tr>
                  <th className="p-3 pl-6 font-label-caps text-on-surface-variant uppercase tracking-wider">Key</th>
                  <th className="p-3 font-label-caps text-on-surface-variant uppercase tracking-wider">Value</th>
                  <th className="p-3 font-label-caps text-on-surface-variant uppercase tracking-wider">Description</th>
                  <th className="p-3 font-label-caps text-on-surface-variant uppercase tracking-wider">Last updated</th>
                  <th className="p-3 pr-6 font-label-caps text-on-surface-variant uppercase tracking-wider"></th>
                </tr>
              </thead>
              <tbody className="font-body-md text-sm">
                {items.map((c) => (
                  <tr key={c.config_key} className="border-b border-outline-variant/50">
                    <td className="p-3 pl-6 font-code-sm text-primary">{c.config_key}</td>
                    <td className="p-3">
                      {editing === c.config_key ? (
                        <input
                          className="w-32 bg-[#131313] border border-primary/50 rounded-md py-1.5 px-2 text-sm text-on-surface font-code-sm focus:outline-none"
                          value={draft}
                          onChange={(e) => setDraft(e.target.value)}
                          autoFocus
                        />
                      ) : (
                        <span className="font-code-sm text-on-surface bg-surface-container-highest px-2 py-1 rounded">{c.config_value}</span>
                      )}
                    </td>
                    <td className="p-3 text-on-surface-variant text-xs max-w-[320px]">{c.description}</td>
                    <td className="p-3 text-on-surface-variant text-xs">{new Date(c.updated_at).toLocaleString()}</td>
                    <td className="p-3 pr-6">
                      {editing === c.config_key ? (
                        <div className="flex gap-2">
                          <button
                            className="px-3 py-1 rounded text-xs font-bold bg-primary text-on-primary hover:bg-primary/90 transition-colors disabled:opacity-60"
                            onClick={() => updateMutation.mutate({ key: c.config_key, value: draft })}
                            disabled={updateMutation.isPending}
                          >
                            Save
                          </button>
                          <button
                            className="px-3 py-1 rounded text-xs font-medium text-on-surface-variant hover:bg-surface-variant/50 transition-colors"
                            onClick={() => setEditing(null)}
                          >
                            Cancel
                          </button>
                        </div>
                      ) : (
                        <button
                          className="px-3 py-1 rounded text-xs font-medium text-on-surface-variant hover:bg-surface-variant/50 transition-colors flex items-center gap-1"
                          onClick={() => {
                            setEditing(c.config_key);
                            setDraft(c.config_value);
                          }}
                        >
                          <span className="material-symbols-outlined text-[14px]">edit</span>
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
