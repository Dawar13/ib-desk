"use client";

// The in-document evidence highlight. Renders the canonical document text and
// highlights the exact span a value was grounded to, using the service-computed
// character offsets from Phase 2. This closes the trust loop: a click shows not
// just the stored sentence but exactly where in the document it came from.
//
// The highlight is into the canonical normalized text the offsets index into,
// not the original PDF's visual layout (that is a separate coordinate-mapping
// problem and out of scope). When a span cannot be resolved, the preview
// degrades to showing the text without an in-line highlight rather than breaking,
// and the stored source sentence is always shown alongside it by the drawer.

import { useEffect, useRef } from "react";

interface DocumentPreviewProps {
  text: string | null | undefined;
  charStart: number | null;
  charEnd: number | null;
}

// A span resolves when there is text and the offsets are integers that fall
// within the text and enclose a non-empty range.
function spanResolves(
  text: string | null | undefined,
  charStart: number | null,
  charEnd: number | null,
): text is string {
  return (
    typeof text === "string" &&
    text.length > 0 &&
    charStart !== null &&
    charEnd !== null &&
    Number.isInteger(charStart) &&
    Number.isInteger(charEnd) &&
    charStart >= 0 &&
    charEnd > charStart &&
    charEnd <= text.length
  );
}

export default function DocumentPreview({
  text,
  charStart,
  charEnd,
}: DocumentPreviewProps) {
  const markRef = useRef<HTMLElement>(null);
  const resolved = spanResolves(text, charStart, charEnd);

  useEffect(() => {
    const node = markRef.current;
    if (!resolved || !node || typeof node.scrollIntoView !== "function") {
      return;
    }
    try {
      node.scrollIntoView({ block: "center" });
    } catch {
      // Some environments (jsdom) do not implement scrollIntoView; ignore.
    }
  }, [resolved, charStart, charEnd, text]);

  if (typeof text !== "string" || text.length === 0) {
    return (
      <p className="text-xs text-faint" data-preview-fallback="true">
        The document text is not available for an in-context preview here.
      </p>
    );
  }

  if (!resolved) {
    return (
      <div>
        <p className="mb-2 text-xs text-faint" data-preview-fallback="true">
          The exact location could not be resolved. The source sentence is shown above.
        </p>
        <pre className="max-h-72 overflow-y-auto whitespace-pre-wrap break-words rounded-md border border-line bg-paper p-3 font-mono text-xs leading-relaxed text-ink">
          {text}
        </pre>
      </div>
    );
  }

  const before = text.slice(0, charStart ?? 0);
  const span = text.slice(charStart ?? 0, charEnd ?? 0);
  const after = text.slice(charEnd ?? 0);

  return (
    <pre
      data-document-preview="true"
      className="max-h-72 overflow-y-auto whitespace-pre-wrap break-words rounded-md border border-line bg-paper p-3 font-mono text-xs leading-relaxed text-ink"
    >
      {before}
      <mark
        ref={markRef}
        data-evidence-highlight="true"
        className="rounded px-0.5 text-ink"
        style={{ backgroundColor: "#f4d97b" }}
      >
        {span}
      </mark>
      {after}
    </pre>
  );
}
