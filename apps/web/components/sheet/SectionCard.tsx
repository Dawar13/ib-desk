"use client";

// One discovered section, rendered in spreadsheet chrome and dispatched to a
// renderer purely by its render hint. There is no business concept here: the same
// six renderers serve any section the engine discovers, for any document. The
// card never inspects the section's meaning, only its render_hint and kind.

import { useMemo, useState } from "react";
import { cx } from "@/lib/cx";
import { categoryAccent } from "@/lib/sheet/category";
import { buildChartData, isChartHint } from "@/lib/sheet/chart";
import ChipList from "./renderers/ChipList";
import KeyValueBlock from "./renderers/KeyValueBlock";
import SectionChart from "./renderers/SectionChart";
import SectionTable from "./renderers/SectionTable";
import SummaryBlock from "./renderers/SummaryBlock";
import type { RendererProps } from "./types";

// The renderer chosen by render hint. Chart hints route through ChartOrTable so
// they get the toggle and the safe fallback; everything else renders directly.
function SectionBody({ section, onEvidence }: RendererProps) {
  switch (section.render_hint) {
    case "keyvalue":
      return <KeyValueBlock section={section} onEvidence={onEvidence} />;
    case "chips":
      return <ChipList section={section} onEvidence={onEvidence} />;
    case "table":
      return <SectionTable section={section} onEvidence={onEvidence} />;
    case "longtext":
      return <SummaryBlock section={section} onEvidence={onEvidence} />;
    case "timeseries_bar":
    case "timeseries_line":
    case "breakdown_pie":
      return <ChartOrTable section={section} onEvidence={onEvidence} />;
    default:
      // Exhaustive over RenderHint today; the table is a safe default if the enum
      // grows before this switch does, so a new hint can never render broken.
      return <SectionTable section={section} onEvidence={onEvidence} />;
  }
}

// A chart-hinted section: the chart with a Chart/Table toggle, or, when the data
// cannot form a sound chart, the table alone with a short note. A chart never
// breaks the page.
function ChartOrTable({ section, onEvidence }: RendererProps) {
  const result = useMemo(() => buildChartData(section), [section]);
  const [view, setView] = useState<"chart" | "table">("chart");

  if (!result.valid || result.data === null) {
    return (
      <div data-chart-fallback="true">
        <p className="mb-2 text-xs text-faint">
          Chart unavailable: fewer than three comparable points. Showing the table.
        </p>
        <SectionTable section={section} onEvidence={onEvidence} />
      </div>
    );
  }

  return (
    <div>
      <div
        role="group"
        aria-label="Chart or table view"
        className="mb-2 inline-flex overflow-hidden border border-line text-xs"
      >
        <button
          type="button"
          onClick={() => setView("chart")}
          aria-pressed={view === "chart"}
          className={cx(
            "px-3 py-1 transition-colors",
            view === "chart" ? "bg-primary text-white" : "bg-surface text-muted hover:bg-primary-tint",
          )}
        >
          Chart
        </button>
        <button
          type="button"
          onClick={() => setView("table")}
          aria-pressed={view === "table"}
          className={cx(
            "border-l border-line px-3 py-1 transition-colors",
            view === "table" ? "bg-primary text-white" : "bg-surface text-muted hover:bg-primary-tint",
          )}
        >
          Table
        </button>
      </div>
      {view === "chart" ? (
        <SectionChart data={result.data} section={section} onEvidence={onEvidence} />
      ) : (
        <SectionTable section={section} onEvidence={onEvidence} />
      )}
    </div>
  );
}

interface SectionCardProps extends RendererProps {
  // Stagger index for the gradual-reveal fade, so sections settle in sequence.
  revealIndex?: number;
}

export default function SectionCard({
  section,
  onEvidence,
  revealIndex = 0,
}: SectionCardProps) {
  const accent = categoryAccent(section.category);
  const chart = isChartHint(section.render_hint);
  // Cap the cumulative delay so a large sheet still settles promptly.
  const delayMs = Math.min(revealIndex, 12) * 60;

  return (
    <section
      data-section-key={section.key}
      data-render-hint={section.render_hint}
      data-section-kind={section.kind}
      data-chart-hint={chart ? "true" : "false"}
      className="animate-sheet-fade-in overflow-hidden border border-line bg-surface"
      style={{ animationDelay: `${delayMs}ms`, borderLeft: `3px solid ${accent}` }}
    >
      <header className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-0.5 border-b border-line bg-paper px-3 py-1.5">
        <h3 className="font-serif text-base font-medium leading-tight text-ink">
          {section.label}
        </h3>
        {section.category ? (
          <span
            className="text-[11px] font-medium uppercase tracking-wide"
            style={{ color: accent }}
          >
            {section.category}
          </span>
        ) : null}
      </header>
      <div className="p-2">
        <SectionBody section={section} onEvidence={onEvidence} />
      </div>
    </section>
  );
}
