"use client";

// Shared sheet primitives: the confidence dot, the universal clickable value, and
// a small empty-state line. Every value in the sheet renders through EvidenceValue
// so the confidence marker and the click-to-evidence interaction are present and
// uniform on every value, in every render hint.

import type { ReactNode } from "react";
import { cx } from "@/lib/cx";
import { confidenceStyle } from "@/lib/sheet/confidence";
import { cellDisplayValue } from "@/lib/sheet/value";
import type { EvidenceHandler, EvidenceTarget } from "./types";

export function ConfidenceDot({ score }: { score: number | null }) {
  const style = confidenceStyle(score);
  return (
    <span
      aria-hidden="true"
      data-confidence-band={style.band}
      title={`Confidence: ${style.label}`}
      className="inline-block h-2 w-2 shrink-0 rounded-full"
      style={{ backgroundColor: style.color }}
    />
  );
}

type ValueVariant = "mono" | "plain" | "prose";

interface EvidenceValueProps {
  target: EvidenceTarget;
  onEvidence: EvidenceHandler;
  // Typography of the value text. mono for numeric and financial values, plain
  // for short text and chips, prose for narrative.
  variant?: ValueVariant;
  // Layout classes for the trigger (padding, chip border, block width). Kept
  // separate from variant so the container layout and the text style never fight.
  className?: string;
  // Optional explicit content; defaults to the cell's display value.
  children?: ReactNode;
}

export function EvidenceValue({
  target,
  onEvidence,
  variant = "plain",
  className,
  children,
}: EvidenceValueProps) {
  const { cell } = target;
  const style = confidenceStyle(cell.confidence);
  const value = cellDisplayValue(cell);
  return (
    <button
      type="button"
      data-evidence="true"
      data-confidence-band={style.band}
      onClick={() => onEvidence(target)}
      title={`${value}. Confidence ${style.label}. Click for the source sentence.`}
      className={cx(
        "group rounded text-left transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-ink/20",
        className,
      )}
    >
      <ConfidenceDot score={cell.confidence} />
      <span
        className={cx(
          variant === "mono" && "font-mono text-sm tabular-nums text-ink",
          variant === "plain" && "text-sm text-ink",
          variant === "prose" && "font-serif text-[15px] leading-relaxed text-ink",
        )}
      >
        {children ?? value}
      </span>
    </button>
  );
}

export function SectionEmpty({ message }: { message?: string }) {
  return (
    <p className="text-sm text-muted">
      {message ?? "No grounded values in this section."}
    </p>
  );
}
