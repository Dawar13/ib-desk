"use client";

// The per-document sheet tab, anchored at the bottom like a spreadsheet tab and
// showing the subject name. One document maps to one sheet, so there is one tab.

interface SheetTabProps {
  subject: string;
}

export default function SheetTab({ subject }: SheetTabProps) {
  return (
    <div className="sticky bottom-0 z-10 flex items-end border-t border-line bg-paper/90 px-4 pt-1 backdrop-blur">
      <span className="-mb-px max-w-xs truncate border border-b-0 border-line bg-surface px-4 py-1.5 font-serif text-sm text-ink">
        {subject}
      </span>
    </div>
  );
}
