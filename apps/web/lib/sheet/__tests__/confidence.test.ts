// Confidence semantics lock (visual restyle gate). The confidence dot colors are
// the one set of colors that carries meaning, so a visual restyle must not touch
// them. This pins the color and the band for high, medium, low, and unscored to
// their exact values; any change to confidence.ts fails here. A failure means the
// trust signal was altered, which is not acceptable in a visual-only change.

import { describe, expect, it } from "vitest";
import { confidenceBand, confidenceStyle } from "@/lib/sheet/confidence";

describe("confidence colors are unchanged by the restyle", () => {
  it("maps each band to its exact color, byte for byte", () => {
    expect(confidenceStyle(0.9).color).toBe("#2f7d5b"); // high
    expect(confidenceStyle(0.6).color).toBe("#bd861f"); // medium
    expect(confidenceStyle(0.3).color).toBe("#b4503e"); // low
    expect(confidenceStyle(null).color).toBe("#9a9182"); // unscored
  });

  it("keeps the bands and thresholds", () => {
    expect(confidenceBand(0.9)).toBe("high");
    expect(confidenceBand(0.8)).toBe("high");
    expect(confidenceBand(0.6)).toBe("medium");
    expect(confidenceBand(0.5)).toBe("medium");
    expect(confidenceBand(0.3)).toBe("low");
    expect(confidenceBand(null)).toBe("unknown");
    expect(confidenceBand(undefined)).toBe("unknown");
    expect(confidenceBand(Number.NaN)).toBe("unknown");
  });
});
