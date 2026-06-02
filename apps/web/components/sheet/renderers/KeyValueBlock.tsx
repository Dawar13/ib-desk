"use client";

// keyvalue renderer. Field and value pairs for scalar sections.
//
// Two compact layouts, chosen by the data, never by inventing anything:
//   - When the cells carry real field labels (col_key set), they render as a
//     two-column definition grid, so the section is about half as tall as a
//     single stacked column and fills the available width.
//   - When a section has no field labels at all (the extraction left col_key
//     null on every cell), the positional "Row N" label is pure noise, so the
//     values pack into a tight wrapped flow with no label column rather than
//     wasting a full row on a meaningless label. We never fabricate a label.
// Numeric values render monospace; text values plain.

import { cellFieldLabel, numericValue } from "@/lib/sheet/value";
import { EvidenceValue, SectionEmpty } from "../primitives";
import type { RendererProps } from "../types";

export default function KeyValueBlock({ section, onEvidence }: RendererProps) {
  if (section.cells.length === 0) {
    return <SectionEmpty />;
  }

  const hasLabels = section.cells.some(
    (cell) => cell.col_key !== null && cell.col_key.trim() !== "",
  );

  if (!hasLabels) {
    // No meaningful labels: a tight wrapped flow of the values, so a long run of
    // short scalars fills the width instead of one sparse, full-width row each.
    return (
      <ul className="flex flex-wrap gap-1.5">
        {section.cells.map((cell) => (
          <li key={cell.id}>
            <EvidenceValue
              target={{ cell, section }}
              onEvidence={onEvidence}
              variant={numericValue(cell) !== null ? "mono" : "plain"}
              className="inline-flex items-center gap-1.5 border border-line bg-paper px-2 py-0.5 hover:bg-ink/[0.05]"
            />
          </li>
        ))}
      </ul>
    );
  }

  // Labelled fields: a two-column definition grid with hairline cell borders, so
  // the block reads like a compact spreadsheet and uses the horizontal space.
  return (
    <dl className="grid grid-cols-1 border-l border-t border-line sm:grid-cols-2">
      {section.cells.map((cell) => (
        <div
          key={cell.id}
          className="flex items-baseline justify-between gap-4 border-b border-r border-line px-2 py-1"
        >
          <dt className="text-sm text-muted">{cellFieldLabel(cell)}</dt>
          <dd className="text-right">
            <EvidenceValue
              target={{ cell, section }}
              onEvidence={onEvidence}
              variant={numericValue(cell) !== null ? "mono" : "plain"}
              className="inline-flex items-center gap-1.5 px-1 py-0.5 hover:bg-ink/[0.04]"
            />
          </dd>
        </div>
      ))}
    </dl>
  );
}
