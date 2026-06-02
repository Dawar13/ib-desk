// Human label for a document's discovered type, used in the subject header as a
// classification chip. A null type (not yet classified) yields no chip rather
// than a guess.

import type { DocType } from "@ib-desk/shared";

const LABELS: Record<DocType, string> = {
  company_profile: "Company profile",
  market_overview: "Market overview",
  deal: "Deal",
  person: "Person",
  technology: "Technology",
  other: "Document",
};

export function docTypeLabel(docType: DocType | null | undefined): string | null {
  if (!docType) {
    return null;
  }
  return LABELS[docType] ?? "Document";
}
