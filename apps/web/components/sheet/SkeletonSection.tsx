"use client";

// A section skeleton shown during the gradual reveal. Before the section's
// per-section event arrives it shimmers as extracting; once it arrives it settles
// to an extracted state. The real values fade in when the run reaches done, since
// persistence is atomic at the end of the run.

import { cx } from "@/lib/cx";

interface SkeletonSectionProps {
  label: string;
  ready: boolean;
}

export default function SkeletonSection({ label, ready }: SkeletonSectionProps) {
  return (
    <section
      data-skeleton="true"
      data-ready={ready ? "true" : "false"}
      className={cx(
        "overflow-hidden rounded-md border border-line bg-surface transition-opacity duration-300",
        ready ? "opacity-100" : "opacity-70",
      )}
    >
      <header className="flex items-center justify-between border-b border-line bg-paper/40 px-4 py-2.5">
        <h3 className="font-serif text-lg leading-tight text-ink">{label}</h3>
        {ready ? (
          <span className="text-xs font-medium" style={{ color: "#2f7d5b" }}>
            Extracted
          </span>
        ) : (
          <span className="flex items-center gap-1.5 text-xs text-faint">
            <span className="h-2 w-2 animate-pulse rounded-full bg-faint" />
            Extracting
          </span>
        )}
      </header>
      <div className="space-y-2 px-4 py-3" aria-hidden="true">
        <div
          className={cx("h-3 rounded bg-line", !ready && "animate-pulse")}
          style={{ width: "70%" }}
        />
        <div
          className={cx("h-3 rounded bg-line", !ready && "animate-pulse")}
          style={{ width: "45%" }}
        />
        <div
          className={cx("h-3 rounded bg-line", !ready && "animate-pulse")}
          style={{ width: "60%" }}
        />
      </div>
    </section>
  );
}
