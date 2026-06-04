import type { Config } from "tailwindcss";
import { palette } from "./lib/theme";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      // Cool blue palette sampled from the owner's sky photo, sourced from
      // lib/theme so class-name consumers and raw-color consumers (recharts)
      // share one definition. These structural tokens are used as static class
      // names (bg-paper, text-ink, border-line, bg-primary), so they are never
      // purged. Category accents and confidence colors are applied as inline
      // styles from data, not class names, since those are data-driven and
      // semantic, and they are intentionally not part of this palette.
      colors: {
        paper: palette.paper,
        surface: palette.surface,
        ink: palette.ink,
        muted: palette.muted,
        faint: palette.faint,
        line: { DEFAULT: palette.line, strong: palette.lineStrong },
        primary: {
          DEFAULT: palette.primary,
          deep: palette.primaryDeep,
          tint: palette.primaryTint,
        },
        cloud: palette.cloud,
      },
      fontFamily: {
        serif: ['Georgia', 'Cambria', '"Times New Roman"', "Times", "serif"],
        mono: [
          "ui-monospace",
          "SFMono-Regular",
          "Menlo",
          "Consolas",
          '"Liberation Mono"',
          "monospace",
        ],
      },
      keyframes: {
        "sheet-fade-in": {
          "0%": { opacity: "0", transform: "translateY(6px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        "sheet-fade-in": "sheet-fade-in 0.45s ease-out both",
      },
    },
  },
  plugins: [],
};

export default config;
