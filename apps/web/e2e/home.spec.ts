import { test, expect } from "@playwright/test";

// Smoke test for the Phase 0 wiring proof. The page fetches client side, so the
// assertions await each text with toBeVisible, which retries until the fetches
// resolve. This proves web to service to database to back is connected and that
// the single seeded sample sheet renders.
test("home page shows connectivity and the seeded sample sheet", async ({
  page,
}) => {
  await page.goto("/");

  await expect(page.getByText("Connected", { exact: true })).toBeVisible();
  await expect(page.getByText("Sample sheet")).toBeVisible();
  // Target the section heading by role. A plain getByText("Overview") would also
  // match the cell text "Sample overview ..." (case-insensitive substring) and
  // trip Playwright strict mode.
  await expect(
    page.getByRole("heading", { name: "Overview", exact: true }),
  ).toBeVisible();
  await expect(page.getByText(/^Sample overview/)).toBeVisible();
});
