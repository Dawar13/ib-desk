"use client";

// keyvalue renderer. A definition list of field and value pairs, one per cell.
// Numeric values render monospace; text values plain. Used for scalar sections.

import { cellFieldLabel, numericValue } from "@/lib/sheet/value";
import { EvidenceValue, SectionEmpty } from "../primitives";
import type { RendererProps } from "../types";

export default function KeyValueBlock({ section, onEvidence }: RendererProps) {
  if (section.cells.length === 0) {
    return <SectionEmpty />;
  }
  return (
    <dl className="divide-y divide-line">
      {section.cells.map((cell) => (
        <div
          key={cell.id}
          className="flex items-baseline justify-between gap-4 py-1"
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
