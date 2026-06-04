// Single source of truth for the IB Desk palette.
//
// Tailwind reads these to generate the structural utility classes (bg-paper,
// text-ink, border-line, bg-primary). The few places that cannot use a class name
// (recharts, which needs raw color strings) import the same values, so every
// color in the product flows from this one file and a restyle is a one-file edit.
//
// The values are sampled from the owner's sky photograph, not invented: the sky
// averages #4F6C9D and the clouds average #C8CBD9, and the neutrals derive from
// those. Semantic colors that carry meaning (the confidence bands and the section
// category accents) live with their data in lib/sheet and are deliberately not
// part of this palette, so a visual restyle can never alter a trust signal.
export const palette = {
  // Neutrals.
  paper: "#F7F8FB", // page background
  surface: "#FFFFFF", // cards and raised surfaces
  ink: "#18202E", // primary text
  muted: "#4A566B", // secondary text
  faint: "#7C879B", // muted text
  line: "#E6EAF1", // hairline borders
  lineStrong: "#D7DEE9", // stronger borders
  // Primary, sampled from the sky.
  primary: "#4F6C9D", // accent
  primaryDeep: "#394E71", // primary buttons and emphasis, white text on top
  primaryTint: "#EAF0F8", // soft fills, hovers, selected states
  // Optional soft cloud wash, used at low opacity where a neutral fill is needed.
  cloud: "#C8CBD9",
} as const;
