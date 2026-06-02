"use client";

// The populated sheet: the subject header, the discovered sections as a vertical
// stack of cards in the engine's order, the sheet tab, and the evidence drawer.
// It owns the selected-evidence state so a click on any value anywhere in the
// stack opens that value's source. It is fully data-driven: give it sections and
// it renders them by render hint, assuming nothing about which sections exist.

import { useState } from "react";
import type { DocType, SectionWithCells } from "@ib-desk/shared";
import EvidenceDrawer from "./EvidenceDrawer";
import SectionCard from "./SectionCard";
import SheetTab from "./SheetTab";
import SubjectHeader from "./SubjectHeader";
import type { EvidenceTarget } from "./types";

interface SheetProps {
  subject: string;
  docType: DocType | null;
  sections: SectionWithCells[];
  fieldCount: number;
}

export default function Sheet({
  subject,
  docType,
  sections,
  fieldCount,
}: SheetProps) {
  const [evidence, setEvidence] = useState<EvidenceTarget | null>(null);

  return (
    <div className="flex h-full flex-col">
      <SubjectHeader
        subject={subject}
        docType={docType}
        sectionCount={sections.length}
        fieldCount={fieldCount}
      />
      <div className="flex-1 overflow-y-auto px-6 py-5">
        {sections.length === 0 ? (
          <p className="text-sm text-muted">
            The extraction produced no grounded sections for this document.
          </p>
        ) : (
          <div className="space-y-5">
            {sections.map((section, index) => (
              <SectionCard
                key={section.id}
                section={section}
                onEvidence={setEvidence}
                revealIndex={index}
              />
            ))}
          </div>
        )}
      </div>
      <SheetTab subject={subject} />
      <EvidenceDrawer target={evidence} onClose={() => setEvidence(null)} />
    </div>
  );
}
