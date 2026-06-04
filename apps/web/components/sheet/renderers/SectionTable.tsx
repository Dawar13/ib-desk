"use client";

// table renderer. A real spreadsheet grid: a header row from the section's columns
// (or columns derived from the data), then one body row per row index, with
// hairline borders on every cell and no rounded corners. Columns size to their
// content, and a long-text cell wraps within a generous maximum width so a wide
// column stays a few lines tall instead of squeezing into a narrow, very tall
// column. The grid scrolls horizontally when it is wider than the view. Each
// present value is clickable for evidence with its confidence dot; a missing cell
// shows a faint placeholder rather than an invented value. Also serves as the
// table view and the safe fallback for chart-hinted sections.

import { tableColumns, tableRows } from "@/lib/sheet/table";
import { NO_VALUE, valueVariant } from "@/lib/sheet/value";
import { EvidenceValue, SectionEmpty } from "../primitives";
import type { RendererProps } from "../types";

export default function SectionTable({ section, onEvidence }: RendererProps) {
  if (section.cells.length === 0) {
    return <SectionEmpty />;
  }
  const columns = tableColumns(section);
  const rows = tableRows(section);

  return (
    <div className="overflow-x-auto border border-line">
      <table className="min-w-full border-collapse text-[13px]">
        <thead>
          <tr>
            {columns.map((column) => (
              <th
                key={column.key}
                scope="col"
                className="border-b border-r border-line bg-paper px-2 py-1 text-left align-bottom font-semibold text-muted last:border-r-0"
              >
                {column.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.rowIdx} className="odd:bg-surface even:bg-paper/40">
              {columns.map((column) => {
                const cell = row.cells[column.key];
                return (
                  <td
                    key={column.key}
                    className="border-b border-r border-line p-0 align-top last:border-r-0"
                  >
                    {cell ? (
                      <EvidenceValue
                        target={{ cell, section }}
                        onEvidence={onEvidence}
                        variant={valueVariant(cell)}
                        className="flex w-full max-w-[26rem] items-start gap-1.5 px-2 py-1 text-left hover:bg-ink/[0.05]"
                      />
                    ) : (
                      <span className="block px-2 py-1 text-faint">{NO_VALUE}</span>
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
