"use client";

import { useCallback, useEffect, useState } from "react";
import type { CreateDocumentResponse, DocumentListItem } from "@ib-desk/shared";
import { listDocuments } from "@/lib/api";
import DocumentSidebar from "@/components/DocumentSidebar";
import IngestPanel from "@/components/IngestPanel";
import DocumentView from "@/components/DocumentView";

// The workspace shell. A left sidebar lists the workspace documents most recent
// first; the main area holds the intake controls (file upload with drag and drop,
// plus a paste control) and, once a document is selected, its sheet workspace,
// which builds and renders the dynamic spreadsheet for that document.
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
    <main className="flex h-screen overflow-hidden bg-paper text-ink">
      <DocumentSidebar
        documents={documents}
        selectedId={selectedId}
        loading={loading}
        error={error}
        onSelect={setSelectedId}
      />

      <div className="flex flex-1 flex-col overflow-y-auto">
        <IngestPanel onCreated={onCreated} />

        {selectedId ? (
          <DocumentView key={selectedId} documentId={selectedId} />
        ) : (
          <div className="flex min-h-[50vh] items-center justify-center p-6 text-center">
            <div className="max-w-md">
              <h2 className="font-serif text-xl text-ink">Your private desk</h2>
              <p className="mt-2 text-sm text-muted">
                Add a document above to build its sheet, or pick one from the
                list. The documents you add here are private to this browser.
              </p>
            </div>
          </div>
        )}
      </div>
    </main>
  );
}
