"use client";

// chips renderer. Each cell is a chip. Used for list sections (names, tags, short
// categorical values). Chips read as plain text, not monospace.

import { EvidenceValue, SectionEmpty } from "../primitives";
import type { RendererProps } from "../types";

export default function ChipList({ section, onEvidence }: RendererProps) {
  if (section.cells.length === 0) {
    return <SectionEmpty />;
  }
  return (
    <ul className="flex flex-wrap gap-2">
      {section.cells.map((cell) => (
        <li key={cell.id}>
          <EvidenceValue
            target={{ cell, section }}
            onEvidence={onEvidence}
            variant="plain"
            className="inline-flex items-center gap-1.5 rounded-full border border-line bg-paper px-2.5 py-1 hover:bg-ink/[0.04]"
          />
        </li>
      ))}
    </ul>
  );
}
