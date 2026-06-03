"use client";

// The sheet download control. Offers the styled xlsx (primary) and the flat csv
// (secondary) from GET /v1/sheets/{id}/export. It is disabled until the sheet is
// done, because there is nothing to export before then. The links are plain
// anchors to the export URL; the server sets Content-Disposition to attachment,
// so the browser downloads the file rather than navigating away.

import { exportUrl } from "@/lib/api";

interface DownloadControlsProps {
  sheetId: string;
  disabled: boolean;
}

export default function DownloadControls({ sheetId, disabled }: DownloadControlsProps) {
  if (disabled) {
    return (
      <span
        data-download-disabled="true"
        aria-disabled="true"
        title="Available once the sheet is built"
        className="cursor-not-allowed px-3 py-1 text-sm text-faint"
      >
        Download
      </span>
    );
  }

  return (
    <span className="inline-flex items-center gap-1.5 text-sm">
      <a
        href={exportUrl(sheetId, "xlsx")}
        data-download="xlsx"
        className="bg-ink px-3 py-1 font-medium text-paper transition-colors hover:bg-ink/90"
      >
        Download Excel
      </a>
      <a
        href={exportUrl(sheetId, "csv")}
        data-download="csv"
        className="px-2 py-1 text-muted underline transition-colors hover:no-underline"
      >
        CSV
      </a>
    </span>
  );
}
