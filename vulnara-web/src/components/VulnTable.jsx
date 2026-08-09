import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { flexRender, getCoreRowModel, getSortedRowModel, useReactTable } from "@tanstack/react-table";
import { SeverityBadge, ConfidenceBar, EmptyState } from "./Primitives";

const SEVERITIES = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"];
const STATUSES = ["OPEN", "REMEDIATED", "ACCEPTED_RISK", "FALSE_POSITIVE"];

const SEVERITY_CHIP = {
  CRITICAL: "bg-error/20 border-error/50 text-error shadow-[0_0_10px_rgba(220,38,38,0.2)]",
  HIGH: "bg-high/20 border-high/40 text-high",
  MEDIUM: "bg-medium/20 border-medium/40 text-medium",
  LOW: "bg-low/20 border-low/40 text-low",
  INFO: "bg-info/20 border-info/40 text-info",
};

export function VulnTable({ vulnerabilities }) {
  const navigate = useNavigate();
  const [sorting, setSorting] = useState([{ id: "severity", desc: false }]);
  const [severityFilter, setSeverityFilter] = useState([]);
  const [statusFilter, setStatusFilter] = useState("");

  const severityRank = { CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3, INFO: 4 };

  const filtered = useMemo(() => {
    return vulnerabilities.filter((v) => {
      if (severityFilter.length && !severityFilter.includes(v.severity)) return false;
      if (statusFilter && v.status !== statusFilter) return false;
      return true;
    });
  }, [vulnerabilities, severityFilter, statusFilter]);

  const columns = useMemo(
    () => [
      {
        accessorKey: "severity",
        header: "Severity",
        sortingFn: (a, b) => severityRank[a.original.severity] - severityRank[b.original.severity],
        cell: (info) => <SeverityBadge severity={info.getValue()} />,
      },
      {
        accessorKey: "host",
        header: "Host/Port",
        cell: (info) => (
          <span className="font-code-sm text-on-surface-variant">
            {info.getValue()}
            {info.row.original.port ? `:${info.row.original.port}` : ""}
          </span>
        ),
      },
      {
        accessorKey: "service_name",
        header: "Service",
        cell: (info) => (
          <span className="flex items-center gap-2 text-on-surface font-medium">
            <span className="material-symbols-outlined text-[16px] text-on-surface-variant">terminal</span>
            {info.getValue() || "—"}
            {info.row.original.service_version ? (
              <span className="text-on-surface-variant/70 text-xs font-normal">{info.row.original.service_version}</span>
            ) : null}
          </span>
        ),
      },
      {
        accessorKey: "cve_id",
        header: "CVE ID",
        cell: (info) =>
          info.getValue() ? (
            <span className="font-code-sm text-primary">{info.getValue()}</span>
          ) : (
            <span className="text-on-surface-variant/70 italic text-xs">unmapped</span>
          ),
      },
      {
        accessorKey: "confidence_score",
        header: "AI Confidence",
        cell: (info) => <ConfidenceBar value={info.getValue()} />,
      },
      {
        accessorKey: "status",
        header: "Status",
        cell: (info) => <span className="text-xs text-on-surface-variant font-medium">{info.getValue().replace(/_/g, " ")}</span>,
      },
    ],
    []
  );

  const table = useReactTable({
    data: filtered,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });

  const toggleSeverity = (s) => {
    setSeverityFilter((prev) => (prev.includes(s) ? prev.filter((x) => x !== s) : [...prev, s]));
  };

  return (
    <div className="bg-surface-container-high rounded-xl border border-outline-variant overflow-hidden flex flex-col shadow-lg shadow-black/20">
      {/* Toolbar */}
      <div className="p-4 border-b border-outline-variant flex flex-col sm:flex-row justify-between items-center gap-4 bg-surface-container-high/80">
        <div className="flex items-center gap-2 flex-wrap w-full sm:w-auto">
          <span className="text-xs text-on-surface-variant uppercase font-label-caps tracking-wider mr-1">Severity:</span>
          {SEVERITIES.map((s) => (
            <button
              key={s}
              onClick={() => toggleSeverity(s)}
              className={`px-3 py-1 rounded border text-xs font-bold font-code-sm transition-colors ${
                severityFilter.includes(s)
                  ? SEVERITY_CHIP[s]
                  : "bg-surface-variant border-outline-variant text-on-surface-variant hover:bg-surface-variant/80"
              }`}
            >
              {s}
            </button>
          ))}
        </div>
        <select
          className="bg-[#131313] border border-outline-variant rounded-md py-1.5 px-3 text-sm text-on-surface focus:outline-none focus:border-primary/50 transition-colors w-full sm:w-auto"
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
        >
          <option value="">All statuses</option>
          {STATUSES.map((s) => (
            <option key={s} value={s}>
              {s.replace(/_/g, " ")}
            </option>
          ))}
        </select>
      </div>

      {filtered.length === 0 ? (
        <EmptyState glyph="filter_alt_off" title="No findings match these filters" description="Clear a filter or wait for the scan to progress." />
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse min-w-[800px]">
            <thead>
              {table.getHeaderGroups().map((hg) => (
                <tr key={hg.id} className="bg-surface-container-low/50 border-b border-outline-variant">
                  {hg.headers.map((header) => (
                    <th
                      key={header.id}
                      onClick={header.column.getToggleSortingHandler()}
                      className="p-3 pl-6 font-label-caps text-on-surface-variant uppercase tracking-wider cursor-pointer select-none first:pl-6"
                    >
                      {flexRender(header.column.columnDef.header, header.getContext())}
                      {{ asc: " ↑", desc: " ↓" }[header.column.getIsSorted()] ?? ""}
                    </th>
                  ))}
                </tr>
              ))}
            </thead>
            <tbody className="font-body-md text-sm">
              {table.getRowModel().rows.map((row) => (
                <tr
                  key={row.id}
                  onClick={() => navigate(`/vulnerabilities/${row.original.vuln_id}`)}
                  className="border-b border-outline-variant/50 data-table-row transition-colors group cursor-pointer"
                >
                  {row.getVisibleCells().map((cell) => (
                    <td key={cell.id} className="p-3 pl-6 first:pl-6">
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
