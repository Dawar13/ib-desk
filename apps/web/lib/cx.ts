// Tiny class-name joiner. Filters out falsey parts so conditional classes read
// cleanly at call sites without pulling in a dependency.
export function cx(
  ...parts: Array<string | false | null | undefined>
): string {
  return parts.filter(Boolean).join(" ");
}
