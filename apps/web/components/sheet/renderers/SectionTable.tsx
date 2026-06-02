"use client";

// table renderer. A real grid with a header row from the section's columns (or
// columns derived from the data) and one body row per row index. Each present
// value is clickable for evidence with its confidence dot; a missing cell shows a
// faint placeholder rather than an invented value. Also serves as the table view
// and the safe fallback for chart-hinted sections.

import { cx } from "@/lib/cx";
import { tableColumns, tableRows } from "@/lib/sheet/table";
import { numericValue, NO_VALUE } from "@/lib/sheet/value";
import { EvidenceValue, SectionEmpty } from "../primitives";
import type { RendererProps } from "../types";

export default function SectionTable({ section, onEvidence }: RendererProps) {
  if (section.cells.length === 0) {
    return <SectionEmpty />;
  }
  const columns = tableColumns(section);
  const rows = tableRows(section);

  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-sm">
        <thead>
          <tr className="border-b border-line text-left">
            {columns.map((column) => (
              <th
                key={column.key}
                scope="col"
                className="px-3 py-2 font-medium text-muted"
              >
                {column.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr
              key={row.rowIdx}
              className="border-b border-line/60 last:border-0 hover:bg-ink/[0.02]"
            >
              {columns.map((column) => {
                const cell = row.cells[column.key];
                return (
                  <td
                    key={column.key}
                    className={cx(
                      "px-3 py-1.5 align-top",
                      cell && numericValue(cell) !== null && "tabular-nums",
                    )}
                  >
                    {cell ? (
                      <EvidenceValue
                        target={{ cell, section }}
                        onEvidence={onEvidence}
                        variant={numericValue(cell) !== null ? "mono" : "plain"}
                        className="inline-flex items-center gap-1.5 px-1 py-0.5 hover:bg-ink/[0.04]"
                      />
                    ) : (
                      <span className="text-faint">{NO_VALUE}</span>
                    )}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
