"use client";

import { useEffect, useState } from "react";
import type { HealthResponse, SheetPayload } from "@ib-desk/shared";
import { getHealth, listDocuments, getSheet } from "@/lib/api";

// Phase 0 wiring proof. This is not the product UI. It calls the three Phase 0
// endpoints in order: health, then the document list, then the first document's
// sheet. It renders a connectivity indicator and the single seeded sheet so we
// can see that web to service to database to back is connected. It must never
// crash when the service is down; in that case it shows Not connected.
export default function Home() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [sheet, setSheet] = useState<SheetPayload | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    async function load(): Promise<void> {
      try {
        const healthResult = await getHealth();
        if (!active) {
          return;
        }
        setHealth(healthResult);

        const documents = await listDocuments();
        if (!active) {
          return;
        }
        const first = documents[0];
        if (first && first.sheet_id) {
          const sheetResult = await getSheet(first.sheet_id);
          if (!active) {
            return;
          }
          setSheet(sheetResult);
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
  }, []);

  const connected = health?.database === "connected";

  return (
    <main className="mx-auto max-w-2xl p-8">
      <h1 className="text-2xl font-semibold">IB Desk</h1>

      <div className="mt-4 flex items-center gap-2">
        <span
          className={
            "inline-block h-3 w-3 rounded-full " +
            (connected ? "bg-green-500" : "bg-red-500")
          }
          aria-hidden="true"
        />
        <span className={connected ? "text-green-700" : "text-red-700"}>
          {connected ? "Connected" : "Not connected"}
        </span>
      </div>

      {loading ? <p className="mt-4 text-gray-500">Loading</p> : null}

      {error ? (
        <p className="mt-4 text-red-700">
          Could not reach the service: {error}
        </p>
      ) : null}

      {sheet ? (
        <section className="mt-6">
          <h2 className="text-xl font-medium">{sheet.sheet.title}</h2>
          {sheet.sections.map((section) => (
            <div key={section.id} className="mt-4">
              <h3 className="font-medium">{section.label}</h3>
              {section.cells.map((cell) => (
                <p key={cell.id} className="mt-1 text-gray-800">
                  {cell.value_norm ?? cell.value_raw ?? ""}
                </p>
              ))}
            </div>
          ))}
        </section>
      ) : null}
    </main>
  );
}
