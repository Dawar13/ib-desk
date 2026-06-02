"use client";

// The primary-subject header strip. Shows the subject name in serif, a doc-type
// classification chip, and the section and value counts, with the confidence
// legend alongside. Built from persisted, always-available data; it does not
// assume any particular identity fields, which keeps it schema-agnostic.

import type { DocType } from "@ib-desk/shared";
import { docTypeLabel } from "@/lib/sheet/docType";
import ConfidenceLegend from "./ConfidenceLegend";

interface SubjectHeaderProps {
  subject: string;
  docType: DocType | null;
  sectionCount: number;
  // The value count once known, or null during the reveal before the sheet is
  // populated, in which case the count line reads as still extracting.
  fieldCount: number | null;
}

export default function SubjectHeader({
  subject,
  docType,
  sectionCount,
  fieldCount,
}: SubjectHeaderProps) {
  const typeLabel = docTypeLabel(docType);
  return (
    <header className="border-b border-line bg-surface px-4 py-2.5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          {typeLabel ? (
            <span className="inline-block border border-line bg-paper px-1.5 py-0.5 text-[11px] font-medium uppercase tracking-wide text-muted">
              {typeLabel}
            </span>
          ) : null}
          <h1
            title={subject}
            className="mt-1 line-clamp-2 break-words font-serif text-xl font-medium leading-snug text-ink"
          >
            {subject}
          </h1>
          <p className="mt-0.5 text-xs text-muted">
            {sectionCount} {sectionCount === 1 ? "section" : "sections"}
            {" · "}
            {fieldCount === null
              ? "extracting values"
              : `${fieldCount} ${fieldCount === 1 ? "value" : "values"}`}
          </p>
        </div>
        <div className="pt-0.5">
          <ConfidenceLegend />
        </div>
      </div>
    </header>
  );
}
