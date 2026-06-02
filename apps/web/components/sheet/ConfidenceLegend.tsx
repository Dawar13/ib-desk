"use client";

// The confidence legend. Maps each dot color to its band so the banker can read
// the trust signal on every value. Driven by the same source as the dots, so the
// two can never disagree.

import { CONFIDENCE_LEGEND } from "@/lib/sheet/confidence";

export default function ConfidenceLegend() {
  return (
    <ul
      aria-label="Confidence legend"
      className="flex flex-wrap items-center gap-x-4 gap-y-1"
    >
      {CONFIDENCE_LEGEND.map((style) => (
        <li
          key={style.band}
          data-legend-band={style.band}
          className="flex items-center gap-1.5 text-xs text-muted"
        >
          <span
            aria-hidden="true"
            className="inline-block h-2 w-2 rounded-full"
            style={{ backgroundColor: style.color }}
          />
          <span>
            {style.label}
            <span className="text-faint"> ({style.description})</span>
          </span>
        </li>
      ))}
    </ul>
  );
}
