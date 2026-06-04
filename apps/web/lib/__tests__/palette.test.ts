// Token sweep gate (visual restyle). Asserts no legacy warm beige hex value
// survives anywhere in the web source outside the token source, so the restyle is
// complete rather than partial. The restyle moved every neutral onto the palette
// in lib/theme.ts; a leftover here would mean a beige remnant shows somewhere in
// the cool blue product.
//
// The semantic palettes carry their own colors with their data and are out of
// scope for this visual change, so they are excluded. The unscored confidence
// color happens to equal the old faint neutral, which is exactly why excluding the
// semantic files is necessary: that one trust color is allowed to keep its value.

import { readdirSync, readFileSync, statSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

const WEB_ROOT = path.resolve(__dirname, "../..");
const SCAN_DIRS = ["app", "components", "lib"];

// The previous warm paper palette, the search list per the spec.
const LEGACY_WARM = ["#f4eee2", "#fffdf9", "#e6ddcc", "#2b2722", "#6c6456", "#9a9182"];

// The token source and the semantic palette files own their colors deliberately.
const EXCLUDED = new Set(
  ["lib/theme.ts", "lib/sheet/confidence.ts", "lib/sheet/category.ts"].map((p) =>
    path.join(WEB_ROOT, p),
  ),
);

function sourceFiles(dir: string): string[] {
  const out: string[] = [];
  for (const entry of readdirSync(dir)) {
    if (entry === "node_modules" || entry === ".next" || entry === "__tests__") {
      continue;
    }
    const full = path.join(dir, entry);
    if (statSync(full).isDirectory()) {
      out.push(...sourceFiles(full));
    } else if (/\.(ts|tsx)$/.test(entry) && !EXCLUDED.has(full)) {
      out.push(full);
    }
  }
  return out;
}

describe("token sweep: no legacy warm hex outside the token source", () => {
  const files = SCAN_DIRS.flatMap((d) => sourceFiles(path.join(WEB_ROOT, d)));

  it("scans a non-trivial number of source files", () => {
    // Guards against the walk silently finding nothing and passing vacuously.
    expect(files.length).toBeGreaterThan(10);
  });

  for (const value of LEGACY_WARM) {
    it(`no source file contains ${value}`, () => {
      const offenders = files.filter((f) =>
        readFileSync(f, "utf8").toLowerCase().includes(value),
      );
      expect(offenders).toEqual([]);
    });
  }
});
