"use client";

// longtext renderer. Narrative summarized into clean prose, one clickable block
// per cell, each carrying its confidence dot and opening its source sentence on
// click. This is how qualitative insight is shown as data, not dropped.

import { EvidenceValue, SectionEmpty } from "../primitives";
import type { RendererProps } from "../types";

export default function SummaryBlock({ section, onEvidence }: RendererProps) {
  if (section.cells.length === 0) {
    return <SectionEmpty />;
  }
  return (
    <div className="space-y-2">
      {section.cells.map((cell) => (
        <EvidenceValue
          key={cell.id}
          target={{ cell, section }}
          onEvidence={onEvidence}
          variant="prose"
          className="flex w-full items-start gap-2 p-2 hover:bg-ink/[0.03]"
        />
      ))}
    </div>
  );
}
