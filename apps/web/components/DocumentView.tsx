"use client";

import { useEffect, useState } from "react";
import type { DocumentDetail } from "@ib-desk/shared";
import { getDocument, originalUrl } from "@/lib/api";
import { sourceKindLabel } from "@/lib/labels";

// The main panel for the selected document. It fetches the full DocumentDetail
// (including raw_text) for the given id and shows the name, source kind, page
// count and character count, a clear not-yet-extracted status, and the parsed
// raw_text rendered as whitespace-preserving preformatted text so the user can
// verify parsing worked. There is no grid, no charts, and no evidence drawer in
// Phase 1.

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
        <p className="text-sm text-gray-500" role="status">
          Loading document
        </p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6">
        <p className="text-sm text-red-700" role="alert">
          Could not load the document: {error}
        </p>
      </div>
    );
  }

  if (!detail) {
    return null;
  }

  const charCount = detail.raw_text.length;

  return (
    <article className="flex h-full flex-col overflow-hidden">
      <header className="border-b border-gray-200 px-6 py-4">
        <h1 className="text-xl font-semibold text-gray-900">{detail.name}</h1>
        <dl className="mt-2 flex flex-wrap gap-x-6 gap-y-1 text-sm text-gray-600">
          <div className="flex gap-1">
            <dt className="font-medium text-gray-500">Source:</dt>
            <dd>{sourceKindLabel(detail.source_kind)}</dd>
          </div>
          {detail.page_count !== null ? (
            <div className="flex gap-1">
              <dt className="font-medium text-gray-500">Pages:</dt>
              <dd>{detail.page_count.toLocaleString()}</dd>
            </div>
          ) : null}
          <div className="flex gap-1">
            <dt className="font-medium text-gray-500">Characters:</dt>
            <dd>{charCount.toLocaleString()}</dd>
          </div>
          <div className="flex gap-1">
            <dt className="font-medium text-gray-500">Original:</dt>
            <dd>
              <a
                href={originalUrl(detail.id)}
                target="_blank"
                rel="noreferrer"
                className="text-blue-600 hover:underline"
              >
                Download
              </a>
            </dd>
          </div>
        </dl>
        <p className="mt-3 inline-block rounded-full bg-amber-100 px-3 py-1 text-xs font-medium text-amber-800">
          Not yet extracted
        </p>
      </header>

      <div className="flex-1 overflow-y-auto px-6 py-4">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-600">
          Parsed text
        </h2>
        <pre className="mt-2 whitespace-pre-wrap break-words rounded-md border border-gray-200 bg-gray-50 p-4 font-mono text-sm leading-relaxed text-gray-800">
          {detail.raw_text}
        </pre>
      </div>
    </article>
  );
}
