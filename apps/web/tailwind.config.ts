import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      // Warm paper palette for the sheet. These structural tokens are used as
      // static class names (bg-paper, text-ink, border-line), so they are never
      // purged. Category accents and confidence colors are applied as inline
      // styles from data, not class names, since those are data-driven.
      colors: {
        paper: "#f4eee2",
        surface: "#fffdf9",
        line: "#e6ddcc",
        ink: "#2b2722",
        muted: "#6c6456",
        faint: "#9a9182",
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
