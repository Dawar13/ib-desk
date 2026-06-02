// The gradual-reveal state machine.
//
// The reveal is driven off the extraction event stream. This reducer folds each
// streamed frame into a small, pure state: the discovered section skeletons (in
// order), which have finished extraction, and the subject classification carried
// by discovery. It is pure and deterministic so the reveal can be tested without
// a live stream, and it ignores frames it does not need (the per-pass started and
// complete markers), which is how it degrades gracefully to a coarser reveal when
// only pass-level events arrive.

import type { DocType } from "@ib-desk/shared";
import { humanizeKey } from "./key";

export interface RevealSkeleton {
  key: string;
  label: string;
}

export interface RevealState {
  // Subject classification from the discovery frame, when present.
  docType: DocType | null;
  primaryTopic: string | null;
  // Discovered sections in engine order; labels are humanized keys until a
  // per-section frame supplies the real label.
  discovered: RevealSkeleton[];
  // Keys of sections that have finished extraction, in arrival order.
  completed: string[];
}

export interface EventFrameInput {
  stage: string;
  message: string | null;
  payload: unknown;
}

export const INITIAL_REVEAL: RevealState = {
  docType: null,
  primaryTopic: null,
  discovered: [],
  completed: [],
};

function asRecord(value: unknown): Record<string, unknown> | null {
  return typeof value === "object" && value !== null
    ? (value as Record<string, unknown>)
    : null;
}

function asString(value: unknown): string | null {
  return typeof value === "string" ? value : null;
}

const DOC_TYPES: readonly DocType[] = [
  "company_profile",
  "market_overview",
  "deal",
  "person",
  "technology",
  "other",
];

function asDocType(value: unknown): DocType | null {
  const text = asString(value);
  return text !== null && (DOC_TYPES as readonly string[]).includes(text)
    ? (text as DocType)
    : null;
}

export function revealReducer(
  state: RevealState,
  frame: EventFrameInput,
): RevealState {
  const payload = asRecord(frame.payload);

  // Discovery complete carries the doc classification and the ordered section
  // keys; discovery started carries no payload and is ignored.
  if (frame.stage === "discovery" && payload && Array.isArray(payload.sections)) {
    const discovered: RevealSkeleton[] = payload.sections
      .map((entry) => asString(entry))
      .filter((key): key is string => key !== null)
      .map((key) => ({ key, label: humanizeKey(key) }));
    return {
      docType: asDocType(payload.doc_type) ?? state.docType,
      primaryTopic: asString(payload.primary_topic) ?? state.primaryTopic,
      discovered,
      completed: state.completed.filter((key) =>
        discovered.some((section) => section.key === key),
      ),
    };
  }

  // A per-section completion frame: mark the section finished and adopt its real
  // label. If discovery was not seen, still record the section so a coarse reveal
  // can show it.
  if (frame.stage === "section" && payload) {
    const key = asString(payload.key);
    if (key === null) {
      return state;
    }
    const label = asString(payload.label) ?? humanizeKey(key);
    const discovered = state.discovered.some((section) => section.key === key)
      ? state.discovered.map((section) =>
          section.key === key ? { key, label } : section,
        )
      : [...state.discovered, { key, label }];
    const completed = state.completed.includes(key)
      ? state.completed
      : [...state.completed, key];
    return { ...state, discovered, completed };
  }

  return state;
}
