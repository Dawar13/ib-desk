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
    <header className="border-b border-line bg-surface px-6 py-5">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          {typeLabel ? (
            <span className="inline-block rounded-full border border-line bg-paper px-2 py-0.5 text-xs font-medium uppercase tracking-wide text-muted">
              {typeLabel}
            </span>
          ) : null}
          <h1 className="mt-1.5 break-words font-serif text-3xl leading-tight text-ink">
            {subject}
          </h1>
          <p className="mt-1 text-sm text-muted">
            {sectionCount} {sectionCount === 1 ? "section" : "sections"}
            {" · "}
            {fieldCount === null
              ? "extracting values"
              : `${fieldCount} ${fieldCount === 1 ? "value" : "values"}`}
          </p>
        </div>
        <div className="pt-1">
          <ConfidenceLegend />
        </div>
      </div>
    </header>
  );
}
