// Anonymous per-visitor workspace id (Phase 5).
//
// Generated once per browser and kept in localStorage, so a returning visitor on
// the same browser keeps their documents, and a different browser is a separate,
// empty space. The id is sent on every request and the service uses it as the
// workspace_id that scopes reads and writes.
//
// This is isolation, not authentication. The id lives in the browser, so the
// protection rests on it being a long, random, unguessable value, which is the
// right level for a trusted person looking at public research, and not enough for
// real client documents. It is generated as a v4 UUID because the service
// validates the workspace id as a UUID.

const STORAGE_KEY = "ibdesk.workspace";

function uuidV4(): string {
  const platform = typeof crypto !== "undefined" ? crypto : undefined;
  if (platform && typeof platform.randomUUID === "function") {
    return platform.randomUUID();
  }
  const bytes = new Uint8Array(16);
  if (platform && typeof platform.getRandomValues === "function") {
    platform.getRandomValues(bytes);
  } else {
    for (let i = 0; i < 16; i += 1) {
      bytes[i] = Math.floor(Math.random() * 256);
    }
  }
  bytes[6] = (bytes[6] & 0x0f) | 0x40; // version 4
  bytes[8] = (bytes[8] & 0x3f) | 0x80; // variant 1
  const hex = Array.from(bytes, (b) => b.toString(16).padStart(2, "0"));
  return (
    hex.slice(0, 4).join("") +
    "-" +
    hex.slice(4, 6).join("") +
    "-" +
    hex.slice(6, 8).join("") +
    "-" +
    hex.slice(8, 10).join("") +
    "-" +
    hex.slice(10, 16).join("")
  );
}

// The current browser's workspace id, creating and persisting one on first use.
// Returns an empty string during server rendering, where there is no browser
// storage; the real id is resolved on the client. localStorage can throw in some
// privacy modes, so that falls back to a fresh per-session id rather than crash.
export function getWorkspaceId(): string {
  if (typeof window === "undefined") {
    return "";
  }
  try {
    let id = window.localStorage.getItem(STORAGE_KEY);
    if (id === null || id === "") {
      id = uuidV4();
      window.localStorage.setItem(STORAGE_KEY, id);
    }
    return id;
  } catch {
    return uuidV4();
  }
}
