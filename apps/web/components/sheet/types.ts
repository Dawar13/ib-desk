// Shared local types for the sheet module.

import type { Cell, SectionWithCells } from "@ib-desk/shared";

// What the evidence drawer needs: the clicked value and the section it sits in,
// so the drawer can show the value, its field and section, its confidence, and
// its stored source sentence.
export interface EvidenceTarget {
  cell: Cell;
  section: SectionWithCells;
}

export type EvidenceHandler = (target: EvidenceTarget) => void;

// Every render-hint renderer takes exactly this: a section and the evidence
// handler. Renderers key off render_hint and kind only, never off the meaning of
// the section.
export interface RendererProps {
  section: SectionWithCells;
  onEvidence: EvidenceHandler;
}
