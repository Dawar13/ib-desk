// Category accent colors.
//
// A discovered section may carry a soft category string (the engine proposes it;
// it is never hardcoded here). The sheet gives each category a stable accent so
// related sections read as a group, without the code ever knowing a category by
// name. The accent is chosen by hashing the category string into a fixed warm
// palette, so the same category always maps to the same accent across runs and
// the mapping needs no registry of business concepts. A missing category gets a
// neutral accent.

const PALETTE = [
  "#8c6b4f",
  "#4f6d8c",
  "#5d7d57",
  "#8c5f6f",
  "#6f5d9c",
  "#9c7a3c",
  "#3f7d7a",
  "#9c5a4a",
];

const NEUTRAL = "#7d756a";

function hashString(value: string): number {
  let hash = 0;
  for (let i = 0; i < value.length; i += 1) {
    hash = (hash * 31 + value.charCodeAt(i)) | 0;
  }
  return Math.abs(hash);
}

export function categoryAccent(category: string | null | undefined): string {
  if (!category || category.trim() === "") {
    return NEUTRAL;
  }
  return PALETTE[hashString(category) % PALETTE.length];
}
