// Gate for the cold-start retry that keeps a free-tier 502 (a sleeping server,
// which returns no CORS headers) from surfacing as a hard failure on first load.

import { describe, expect, it, vi } from "vitest";
import { withColdStartRetry } from "@/lib/api";

describe("withColdStartRetry (free-tier cold start)", () => {
  it("retries on failure, then resolves, signaling waking on each retry", async () => {
    let calls = 0;
    const fn = vi.fn(async () => {
      calls += 1;
      if (calls < 3) {
        throw new Error("cold");
      }
      return "ok";
    });
    const onWaking = vi.fn();

    const result = await withColdStartRetry(fn, onWaking, [1, 1, 1]);

    expect(result).toBe("ok");
    expect(fn).toHaveBeenCalledTimes(3);
    expect(onWaking).toHaveBeenCalledTimes(2);
  });

  it("gives up with the last error after exhausting the retries", async () => {
    const fn = vi.fn(async () => {
      throw new Error("still down");
    });

    await expect(withColdStartRetry(fn, undefined, [1, 1])).rejects.toThrow(
      "still down",
    );
    // Two delays means three attempts in total.
    expect(fn).toHaveBeenCalledTimes(3);
  });
})
