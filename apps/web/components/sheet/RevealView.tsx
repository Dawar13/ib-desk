"use client";

// The gradual-reveal view shown while extraction runs. It renders a skeleton per
// discovered section in engine order, settling each as its per-section event
// arrives. The real values fade in when the run reaches done and this is replaced
// by the populated sheet.

import type { DocType } from "@ib-desk/shared";
import type { RevealState } from "@/lib/sheet/reveal";
import SheetTab from "./SheetTab";
import SkeletonSection from "./SkeletonSection";
import SubjectHeader from "./SubjectHeader";

interface RevealViewProps {
  subject: string;
  docType: DocType | null;
  reveal: RevealState;
}

export default function RevealView({ subject, docType, reveal }: RevealViewProps) {
  const completed = new Set(reveal.completed);
  return (
    <div>
      <SubjectHeader
        subject={subject}
        docType={docType}
        sectionCount={reveal.discovered.length}
        fieldCount={null}
      />
      <div className="px-4 py-4">
        <div className="space-y-3">
          {reveal.discovered.map((section) => (
            <SkeletonSection
              key={section.key}
              label={section.label}
              ready={completed.has(section.key)}
            />
          ))}
        </div>
      </div>
      <SheetTab subject={subject} />
    </div>
  );
}
