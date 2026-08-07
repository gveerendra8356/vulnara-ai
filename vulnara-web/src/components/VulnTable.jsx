import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { flexRender, getCoreRowModel, getSortedRowModel, useReactTable } from "@tanstack/react-table";
import { SeverityBadge, ConfidenceBar, EmptyState } from "./Primitives";

const SEVERITIES = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"];
const STATUSES = ["OPEN", "REMEDIATED", "ACCEPTED_RISK", "FALSE_POSITIVE"];

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
        header: "Host",
        cell: (info) => <span className="mono">{info.getValue()}</span>,
      },
      {
        accessorKey: "port",
        header: "Port",
        cell: (info) => <span className="mono">{info.getValue() ?? "—"}</span>,
      },
      {
        accessorKey: "service_name",
        header: "Service",
        cell: (info) => (
          <span>
            {info.getValue() || "—"}
            {info.row.original.service_version ? (
              <span className="small-note"> {info.row.original.service_version}</span>
            ) : null}
          </span>
        ),
      },
      {
        accessorKey: "cve_id",
        header: "CVE",
        cell: (info) => (info.getValue() ? <span className="mono">{info.getValue()}</span> : <span className="small-note">unmapped</span>),
      },
      {
        accessorKey: "confidence_score",
        header: "AI confidence",
        cell: (info) => <ConfidenceBar value={info.getValue()} />,
      },
      {
        accessorKey: "status",
        header: "Status",
        cell: (info) => <span className="small-note">{info.getValue().replace("_", " ")}</span>,
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
    <div className="panel">
      <div className="toolbar">
        <span className="small-note" style={{ marginRight: 4 }}>
          SEVERITY
        </span>
        {SEVERITIES.map((s) => (
          <button key={s} className={`chip-toggle${severityFilter.includes(s) ? " active" : ""}`} onClick={() => toggleSeverity(s)}>
            {s}
          </button>
        ))}
        <div className="spacer" />
        <select className="select" style={{ maxWidth: 190 }} value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
          <option value="">All statuses</option>
          {STATUSES.map((s) => (
            <option key={s} value={s}>
              {s.replace("_", " ")}
            </option>
          ))}
        </select>
      </div>

      {filtered.length === 0 ? (
        <EmptyState glyph="◌" title="No findings match these filters" description="Clear a filter or wait for the scan to progress." />
      ) : (
        <div className="scroll-x">
          <table className="data-table">
            <thead>
              {table.getHeaderGroups().map((hg) => (
                <tr key={hg.id}>
                  {hg.headers.map((header) => (
                    <th key={header.id} onClick={header.column.getToggleSortingHandler()}>
                      {flexRender(header.column.columnDef.header, header.getContext())}
                      {{ asc: " ↑", desc: " ↓" }[header.column.getIsSorted()] ?? ""}
                    </th>
                  ))}
                </tr>
              ))}
            </thead>
            <tbody>
              {table.getRowModel().rows.map((row) => (
                <tr key={row.id} onClick={() => navigate(`/vulnerabilities/${row.original.vuln_id}`)}>
                  {row.getVisibleCells().map((cell) => (
                    <td key={cell.id}>{flexRender(cell.column.columnDef.cell, cell.getContext())}</td>
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
