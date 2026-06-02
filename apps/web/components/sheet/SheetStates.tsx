"use client";

// The non-sheet states: idle (never extracted), loading (fetching a finished
// sheet), discovering (extraction started, structure not yet known), and failed.
// The done and extracting states render the sheet and the reveal respectively.

export function EmptyState() {
  return (
    <div className="flex min-h-[50vh] items-center justify-center p-10 text-center">
      <div className="max-w-sm">
        <h2 className="font-serif text-xl text-ink">No sheet yet</h2>
        <p className="mt-2 text-sm text-muted">
          This document has not been extracted. Build the sheet to turn it into a
          grounded, structured view where every value links to its source.
        </p>
      </div>
    </div>
  );
}

export function LoadingState() {
  return (
    <div className="flex min-h-[50vh] items-center justify-center p-10">
      <p className="text-sm text-muted" role="status">
        Loading the sheet
      </p>
    </div>
  );
}

export function DiscoveringState() {
  return (
    <div className="flex min-h-[50vh] items-center justify-center p-10 text-center">
      <div className="max-w-sm">
        <div
          aria-hidden="true"
          className="mx-auto h-6 w-6 animate-spin rounded-full border-2 border-line border-t-ink"
        />
        <h2 className="mt-4 font-serif text-xl text-ink">Discovering structure</h2>
        <p className="mt-2 text-sm text-muted" role="status">
          Working out what this document is about and which sections fit it.
        </p>
      </div>
    </div>
  );
}

export function FailedState({ message }: { message: string | null }) {
  return (
    <div className="flex min-h-[50vh] items-center justify-center p-10 text-center">
      <div className="max-w-md">
        <h2 className="font-serif text-xl text-ink">Extraction failed</h2>
        <p className="mt-2 text-sm" style={{ color: "#b4503e" }} role="alert">
          {message ?? "The extraction did not complete. You can try again."}
        </p>
        <p className="mt-2 text-sm text-muted">
          Use Re-extract above to run it again.
        </p>
      </div>
    </div>
  );
}
