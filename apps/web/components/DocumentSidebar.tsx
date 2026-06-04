"use client";

import type { DocumentListItem } from "@ib-desk/shared";
import { sourceKindLabel } from "@/lib/labels";

// The left sidebar. Lists documents most recent first (the service already
// orders by created_at desc) and shows a clear empty state when there are none.
// Clicking a document selects it. The list and selection are owned by the page;
// this component is presentational and reports clicks upward.

interface DocumentSidebarProps {
  documents: DocumentListItem[];
  selectedId: string | null;
  loading: boolean;
  // True while the first request is retrying through a free-tier cold start.
  warming?: boolean;
  error: string | null;
  onSelect: (id: string) => void;
}

function metaLine(doc: DocumentListItem): string {
  const parts: string[] = [sourceKindLabel(doc.source_kind)];
  if (doc.page_count !== null) {
    parts.push(doc.page_count + (doc.page_count === 1 ? " page" : " pages"));
  }
  parts.push(doc.char_count.toLocaleString() + " chars");
  return parts.join(" - ");
}

export default function DocumentSidebar({
  documents,
  selectedId,
  loading,
  warming = false,
  error,
  onSelect,
}: DocumentSidebarProps) {
  return (
    <nav
      aria-label="Documents"
      className="flex w-72 shrink-0 flex-col border-r border-gray-200 bg-gray-50"
    >
      <div className="border-b border-gray-200 px-4 py-3">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-600">
          Documents
        </h2>
      </div>

      <div className="flex-1 overflow-y-auto">
        {error ? (
          <p className="px-4 py-3 text-sm text-red-700" role="alert">
            Could not load documents: {error}
          </p>
        ) : warming ? (
          <p className="px-4 py-3 text-sm text-gray-600" role="status">
            Waking the server. The free instance sleeps when idle, so the first
            load after a while can take up to a minute.
          </p>
        ) : loading ? (
          <p className="px-4 py-3 text-sm text-gray-500">Loading documents</p>
        ) : documents.length === 0 ? (
          <div className="px-4 py-6 text-sm text-gray-500">
            <p className="font-medium text-gray-700">No documents yet</p>
            <p className="mt-1">
              Upload a PDF or DOCX, or paste text, to get started.
            </p>
          </div>
        ) : (
          <ul>
            {documents.map((doc) => {
              const selected = doc.id === selectedId;
              return (
                <li key={doc.id}>
                  <button
                    type="button"
                    aria-current={selected ? "true" : undefined}
                    onClick={() => onSelect(doc.id)}
                    className={
                      "block w-full border-b border-gray-100 px-4 py-3 text-left transition-colors " +
                      (selected
                        ? "bg-white font-medium text-gray-900"
                        : "text-gray-700 hover:bg-gray-100")
                    }
                  >
                    <span className="block truncate">{doc.name}</span>
                    <span className="mt-1 block truncate text-xs text-gray-500">
                      {metaLine(doc)}
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </nav>
  );
}
