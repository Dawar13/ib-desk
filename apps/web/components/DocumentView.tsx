"use client";

import { useEffect, useState } from "react";
import type { DocumentDetail } from "@ib-desk/shared";
import { getDocument, originalUrl } from "@/lib/api";
import { sourceKindLabel } from "@/lib/labels";
import SheetWorkspace from "@/components/sheet/SheetWorkspace";

// The main panel for the selected document. It fetches the full DocumentDetail
// (including raw_text) and shows a compact document header, then the sheet
// workspace, which is the product surface: it triggers the engine, reveals the
// sheet section by section off the live event stream, renders every discovered
// section by its render hint with confidence markers and click-to-evidence, and
// handles every state. Before extraction the workspace shows the parsed text so a
// freshly ingested document is still useful.

interface DocumentViewProps {
  documentId: string;
}

export default function DocumentView({ documentId }: DocumentViewProps) {
  const [detail, setDetail] = useState<DocumentDetail | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);
    setDetail(null);

    async function load(): Promise<void> {
      try {
        const result = await getDocument(documentId);
        if (active) {
          setDetail(result);
        }
      } catch (err) {
        if (active) {
          setError(err instanceof Error ? err.message : "Unknown error");
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    void load();

    return () => {
      active = false;
    };
  }, [documentId]);

  if (loading) {
    return (
      <div className="p-6">
        <p className="text-sm text-muted" role="status">
          Loading document
        </p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6">
        <p className="text-sm" style={{ color: "#b4503e" }} role="alert">
          Could not load the document: {error}
        </p>
      </div>
    );
  }

  if (!detail) {
    return null;
  }

  const charCount = detail.raw_text.length;

  const parsedPreview = (
    <div className="px-6 py-4">
      <h2 className="text-xs font-semibold uppercase tracking-wide text-muted">
        Parsed text
      </h2>
      <pre className="mt-2 whitespace-pre-wrap break-words rounded-md border border-line bg-paper p-4 font-mono text-sm leading-relaxed text-ink">
        {detail.raw_text}
      </pre>
    </div>
  );

  return (
    <article>
      <header className="sticky top-0 z-20 border-b border-line bg-surface px-6 py-3">
        <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
          <h1 className="font-mono text-sm text-ink">{detail.name}</h1>
          <dl className="flex flex-wrap gap-x-5 gap-y-1 text-xs text-muted">
            <div className="flex gap-1">
              <dt className="text-faint">Source:</dt>
              <dd>{sourceKindLabel(detail.source_kind)}</dd>
            </div>
            {detail.page_count !== null ? (
              <div className="flex gap-1">
                <dt className="text-faint">Pages:</dt>
                <dd>{detail.page_count.toLocaleString()}</dd>
              </div>
            ) : null}
            <div className="flex gap-1">
              <dt className="text-faint">Characters:</dt>
              <dd>{charCount.toLocaleString()}</dd>
            </div>
            <div className="flex gap-1">
              <dt className="text-faint">Original:</dt>
              <dd>
                <a
                  href={originalUrl(detail.id)}
                  target="_blank"
                  rel="noreferrer"
                  className="text-ink underline hover:no-underline"
                >
                  Download
                </a>
              </dd>
            </div>
          </dl>
        </div>
      </header>

      {detail.sheet_id !== null ? (
        <SheetWorkspace
          key={detail.sheet_id}
          sheetId={detail.sheet_id}
          initialStatus={detail.sheet_status ?? "idle"}
          docName={detail.name}
          docType={detail.doc_type}
          primaryTopic={detail.primary_topic}
          documentText={detail.raw_text}
          idleContent={parsedPreview}
        />
      ) : (
        parsedPreview
      )}
    </article>
  );
}
