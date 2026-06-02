// Humanize a section key into a readable label. Used for reveal skeletons before
// the section's real label has arrived on the event stream. Pure and dependency
// free so it is trivial to test.
export function humanizeKey(key: string): string {
  const cleaned = key.replace(/[_-]+/g, " ").trim();
  if (cleaned === "") {
    return key;
  }
  return cleaned.charAt(0).toUpperCase() + cleaned.slice(1);
}
