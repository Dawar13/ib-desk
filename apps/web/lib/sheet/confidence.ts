// Confidence bands and their visual treatment.
//
// Every grounded value carries an optional confidence score in 0..1. The sheet
// shows a small color-coded dot on each value so the banker can see at a glance
// how sure the engine is, and a legend maps the colors to the bands. The bands
// and thresholds are product decisions and live here so the dot and the legend
// can never disagree. A null or non-numeric score is treated as unscored rather
// than guessed at, in keeping with the no-fabrication rule.

export type ConfidenceBand = "high" | "medium" | "low" | "unknown";

export interface ConfidenceStyle {
  band: ConfidenceBand;
  label: string;
  // Hex applied as an inline style (not a Tailwind class) because the value is
  // data-driven and would otherwise be purged from the stylesheet.
  color: string;
  // Human description of the band, shown in the legend.
  description: string;
}

// A score at or above HIGH is high confidence; at or above MEDIUM is medium;
// below MEDIUM but scored is low; absent is unknown.
export const CONFIDENCE_HIGH = 0.8;
export const CONFIDENCE_MEDIUM = 0.5;

export function confidenceBand(
  score: number | null | undefined,
): ConfidenceBand {
  if (score === null || score === undefined || Number.isNaN(score)) {
    return "unknown";
  }
  if (score >= CONFIDENCE_HIGH) {
    return "high";
  }
  if (score >= CONFIDENCE_MEDIUM) {
    return "medium";
  }
  return "low";
}

const STYLES: Record<ConfidenceBand, ConfidenceStyle> = {
  high: {
    band: "high",
    label: "High",
    color: "#2f7d5b",
    description: "0.80 and above",
  },
  medium: {
    band: "medium",
    label: "Medium",
    color: "#bd861f",
    description: "0.50 to 0.79",
  },
  low: {
    band: "low",
    label: "Low",
    color: "#b4503e",
    description: "below 0.50",
  },
  unknown: {
    band: "unknown",
    label: "Unscored",
    color: "#9a9182",
    description: "no score reported",
  },
};

export function confidenceStyle(
  score: number | null | undefined,
): ConfidenceStyle {
  return STYLES[confidenceBand(score)];
}

// The legend, in descending confidence order, ending with the unscored band.
export const CONFIDENCE_LEGEND: ConfidenceStyle[] = [
  STYLES.high,
  STYLES.medium,
  STYLES.low,
  STYLES.unknown,
];
