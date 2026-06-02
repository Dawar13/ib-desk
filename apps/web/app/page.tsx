"use client";

import { useCallback, useEffect, useState } from "react";
import type { CreateDocumentResponse, DocumentListItem } from "@ib-desk/shared";
import { listDocuments } from "@/lib/api";
import DocumentSidebar from "@/components/DocumentSidebar";
import IngestPanel from "@/components/IngestPanel";
import DocumentView from "@/components/DocumentView";

// The Phase 1 ingestion UI. A left sidebar lists the workspace documents most
// recent first; the main area holds the intake controls (file upload with drag
// and drop, plus a paste control) and, once a document is selected, its parsed
// text preview. There is no extraction, grid, charts, or evidence drawer here:
// Phase 1 only gets a document into the system as clean text and lets the user
// verify the parse.
export default function Home() {
  const [documents, setDocuments] = useState<DocumentListItem[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async (): Promise<DocumentListItem[]> => {
    setError(null);
    try {
      const items = await listDocuments();
      setDocuments(items);
      return items;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
      return [];
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const onCreated = useCallback(
    (response: CreateDocumentResponse): void => {
      // Refresh the list and select the new document so the user immediately
      // sees the parsed text and can confirm the parse worked.
      setSelectedId(response.document_id);
      void refresh();
    },
    [refresh],
  );

  return (
    <main className="flex h-screen overflow-hidden bg-white text-gray-900">
      <DocumentSidebar
        documents={documents}
        selectedId={selectedId}
        loading={loading}
        error={error}
        onSelect={setSelectedId}
      />

      <div className="flex flex-1 flex-col overflow-hidden">
        <IngestPanel onCreated={onCreated} />

        <div className="flex-1 overflow-hidden">
          {selectedId ? (
            <DocumentView key={selectedId} documentId={selectedId} />
          ) : (
            <div className="flex h-full items-center justify-center p-6 text-center text-gray-500">
              <p>
                Select a document from the list, or add one above, to see its
                parsed text.
              </p>
            </div>
          )}
        </div>
      </div>
    </main>
  );
}
