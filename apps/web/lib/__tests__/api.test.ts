// Gate for the cold-start retry that keeps a free-tier 502 (a sleeping server,
// which returns no CORS headers) from surfacing as a hard failure on first load.

import { describe, expect, it, vi } from "vitest";
import { IngestError, isColdStartError, withColdStartRetry } from "@/lib/api";

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

  it("does not retry when shouldRetry rejects the error (a real validation error)", async () => {
    const fn = vi.fn(async () => {
      throw new IngestError("too large", "file_too_large", 413);
    });
    await expect(
      withColdStartRetry(fn, undefined, [1, 1, 1], isColdStartError),
    ).rejects.toThrow("too large");
    // A 4xx is not a cold start, so it surfaces immediately without retrying.
    expect(fn).toHaveBeenCalledTimes(1);
  });
});

describe("isColdStartError", () => {
  it("treats a network failure and a 5xx as a cold start", () => {
    expect(isColdStartError(new TypeError("Failed to fetch"))).toBe(true);
    expect(isColdStartError(new IngestError("bad gateway", null, 502))).toBe(true);
    expect(isColdStartError(new IngestError("unavailable", null, 503))).toBe(true);
  });

  it("does not treat a contract 4xx as a cold start", () => {
    expect(isColdStartError(new IngestError("too large", "file_too_large", 413))).toBe(false);
    expect(isColdStartError(new IngestError("unsupported", "unsupported_type", 415))).toBe(false);
    expect(isColdStartError(new Error("some other error"))).toBe(false);
  });
})
