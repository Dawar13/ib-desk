import fs from "node:fs";
import path from "node:path";
import { test, expect } from "@playwright/test";

// Headline ingestion-through-the-UI test. It uploads a born-digital sample PDF
// via the file input, waits for the document to appear in the sidebar, selects
// it, and asserts both the parsed text (which contains the marker
// "born-digital PDF") and the "Not yet extracted" status are visible. This
// proves the full Phase 1 path through the browser: POST /v1/documents, the
// list refresh, selection, and GET /v1/documents/{id} rendering the parsed text.
//
// The fixture PDF is generated from the Python born_digital_pdf() fixture by the
// orchestrator and CI. Locally, without the fixture, the test skips gracefully
// rather than hard-failing. The path comes from E2E_PDF_FIXTURE if set,
// otherwise the repo-relative apps/web/e2e/sample.pdf.

// Playwright runs with the web app as its working directory, so the repo-relative
// fallback resolves to apps/web/e2e/sample.pdf. CI sets E2E_PDF_FIXTURE to an
// absolute path so the headline test runs rather than skips.
const fixturePath =
  process.env.E2E_PDF_FIXTURE || path.join(process.cwd(), "e2e", "sample.pdf");

test("upload a PDF through the UI and preview its parsed text", async ({
  page,
}) => {
  test.skip(
    !fs.existsSync(fixturePath),
    "PDF fixture not found at " + fixturePath + "; set E2E_PDF_FIXTURE.",
  );

  await page.goto("/");

  // Upload via the hidden file input. setInputFiles drives it regardless of the
  // visible drag-and-drop affordance. The input is labeled for an unambiguous
  // locator.
  await page
    .getByLabel("Choose a file to upload")
    .setInputFiles(fixturePath);

  // Target the uploaded document specifically. The sidebar may already contain a
  // seeded sample document, so the first button is not necessarily the upload;
  // matching the file name avoids selecting the wrong row (which would override
  // the auto-selection of the new document). first() tolerates a database that
  // already holds an earlier sample.pdf from a prior run.
  const sidebar = page.getByRole("navigation", { name: "Documents" });
  const uploaded = sidebar.getByRole("button", { name: /sample\.pdf/ }).first();
  await expect(uploaded).toBeVisible({ timeout: 30000 });

  await uploaded.click();

  // The selected document panel renders the parsed text and the not-yet-extracted
  // status. The marker text proves the PDF parse and normalization round-tripped
  // through the service and back into the preview.
  await expect(page.getByText(/born-digital PDF/)).toBeVisible({
    timeout: 30000,
  });
  await expect(
    page.getByText("Not yet extracted", { exact: true }),
  ).toBeVisible();
});
