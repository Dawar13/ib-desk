# IB Desk

This file is the project context for Claude Code. It is the constitution: the principles and conventions that hold across the whole build. The companion file `BUILD_PLAN.md` is the blueprint: it holds the architecture, the data model, the extraction contracts, the API, and the phase roadmap. Read both before writing code. If reality diverges from either file during the build, update the file rather than letting the code and the docs drift apart.

## 1. What IB Desk is

A banker uploads a research document about anything: a company, a market, a person, a technology, or a deal. IB Desk works out what the document is about, discovers the structure that fits it, extracts everything useful from it, grounds every item back to its source, and renders one clean, dynamic spreadsheet per document. The banker can download a styled, editable workbook that looks as good as the screen. The first user is a new boutique M&A advisory firm, used internally at first.

## 2. Who it serves and the value lodestar

The user is a working M&A and investment banking professional. The single test for every feature and every extracted item is this: does it help the banker understand a target or a market faster and act on it. Value is not only numbers. A well-summarized qualitative insight is data. A clear statement of who the buyers might be, why a founder may be ready to sell, or what makes a market attractive is often worth more than a revenue figure.

## 3. Non-negotiable product principles

1. The schema is discovered, never hardcoded. The code must never assume the document is about a company. The structure of every sheet is decided per document, at runtime, from the content.
2. Content determinism. The same document must yield the same set of relevant data and the same values across runs. Section ordering and visual positioning may vary between runs. The data and the values may not. Where a value is X in one generation, it must be X in every generation.
3. Exhaustive and general. Capture everything useful, structured or qualitative. Important narrative is summarized into clean insight sections, not dropped because it is not a number. Aim for coverage, not a tidy minimum.
4. Always grounded. Every value carries the exact supporting sentence from the source, its character span into the source text, and a confidence score. If it is not supported by the source, it does not appear.
5. Never fabricate. When support is weak, omit the item or flag it with low confidence. This is the cardinal rule. A single invented figure in front of a client destroys trust in the entire product.
6. One document maps to one sheet. Documents are never merged into a shared sheet.
7. Export fidelity. The downloaded file looks as good as the on-screen sheet and stays editable, with color and native charts. This is done server-side, where full styling is possible.
8. Storage is generic and tidy. The user interface and the export are derived from the stored schema. The schema lives as rows of data, not as named tables in code.

## 4. The hard problems and the stance on each

Schema stability. Asking a model to invent the structure means the same document can produce slightly different schemas across runs. The stance: temperature zero, a stable prompt, a soft taxonomy of common section types that nudges the model toward consistent keys without caging it, deterministic normalization of values, and a verification pass. Be honest about the limit: a model at temperature zero is near-deterministic, not perfectly guaranteed. So normalization and verification, not the model alone, carry the burden of value consistency.

Exhaustiveness including qualitative insight. The stance: the discovery pass must propose qualitative insight sections, not only numeric ones, and the extraction pass must summarize important narrative into clean prose rather than discarding it. The unit of value is anything that helps the banker, in whatever shape it appears in the source.

Grounding and no fabrication. The stance: every value is tied to a verbatim source sentence and a character span, a verification pass checks that the sentence truly supports the value, and anything that fails is dropped or flagged. Omission is always preferable to a guess.

Phase 2 note. The character span is service-computed, not model-reported. The model returns a value and its verbatim supporting sentence only; the grounding step locates that sentence in the source text and computes the character offsets, and `value_norm` is computed deterministically by the service. A value whose supporting sentence cannot be located is ungrounded and is dropped. This is the cardinal anti-fabrication mechanism and it is unchanged. Separately, the labeled golden-set eval was descoped by the owner in this build and replaced by a label-free eval (fabrication rate, grounding resolution, value-level stability) plus the secret-free cassette logic gates. The descope does not weaken the grounding rule or the no-fabrication rule. See BUILD_PLAN.md, the Evaluation section, for detail.

## 5. Architecture and interfaces

The full architecture, the generic data model, the discovery and extraction JSON contracts, the API routes, and the render-hint enum live in `BUILD_PLAN.md`. In short: a Next.js web app, a FastAPI service, Postgres with pgvector, OpenAI models, and an xlsxwriter export. The extraction runs as four passes: discovery, extraction, verification, and render typing. The store is generic: documents, sheets, sections, and cells, where one row in cells is one grounded fact.

## 6. Tech stack and repository layout

Web: Next.js, TypeScript in strict mode, React, Tailwind for layout, a data grid, recharts for in-app charts.
Service: Python, FastAPI, async, pydantic models, xlsxwriter for export.
Database: Supabase Postgres with row level security, pgvector reserved for future similar-sheet search.
Object storage: for the original uploaded files.
Models: a flagship OpenAI model for discovery and extraction, a cheaper model for verification. Exact model strings are provided by the project owner. Every model call uses structured outputs so JSON is reliable.

```
ib-desk/
  apps/web/          # Next.js
  services/api/      # FastAPI
  packages/shared/   # shared TypeScript types for the sheet payload
  db/migrations/
  evals/             # golden documents and the evaluation harness
  CLAUDE.md
  BUILD_PLAN.md
```

## 7. The extraction prompts: design rules

The product lives or dies on model behavior, so the discovery, extraction, and verification prompts must be designed deliberately. The actual prompts are delivered in the phase specs. They must encode the following:

- Discover the core topic first, classify the document type, then propose sections that fit the document, including qualitative insight sections, not only numeric ones.
- Be exhaustive. Extract every instance present. Summarize important narrative into clean prose. Do not drop qualitative value because it is not structured.
- Be deterministic in content. Map to stable section keys via the soft taxonomy. Normalize values consistently so the same underlying fact renders identically on every run.
- Ground everything. Every value needs a verbatim supporting sentence and a character span. No support means no output.
- Never fabricate. Prefer omission. Where confidence is low, say so through the confidence score rather than presenting a guess as fact.
- Optimize for banker relevance. Prioritize what helps assess a target, a buyer, a market, or a deal.

## 8. Coding conventions

- TypeScript in strict mode. Python fully typed with pydantic. Tests are required, not optional.
- No em-dashes in any generated documentation, code comment, or interface copy. No emojis anywhere in the product or the docs.
- Clean, aligned, readable formatting.
- Honesty in code and content. Never present invented data as real. Any sample or fixture data must be clearly labeled as sample. Never invent a source, a number, a citation, or a URL.
- Secrets come from environment variables and are never committed.
- Small, phase-scoped changes. Conventional commit messages.

## 9. Security and confidentiality

This is finance research data and some of it will be sensitive. Enforce row level security by workspace. Decide data retention and encryption explicitly. Before any real client document is loaded, confirm whether documents may be sent to a third-party model at all. Treat this as a gating decision, not an afterthought.

## 10. How phases work

The build proceeds one phase at a time. The project owner provides each phase spec as a separate input. Every phase spec will contain, and Claude Code must treat as a contract, the following four parts:

- Summary. One paragraph stating the goal and the scope of the phase.
- Build instructions. The end-to-end steps to implement the phase.
- Tests. Each test states what it checks and what a pass or a failure means, so a red test has a clear interpretation rather than only a status.
- Definition of success. The explicit acceptance bar for the phase.

Rules for execution:

- Do exactly one phase at a time. Do not implement anything from a future phase.
- Do not advance to the next phase until every test passes and the definition of success is met.
- If a decision is genuinely ambiguous, ask the project owner rather than guessing.
- Keep `CLAUDE.md` and `BUILD_PLAN.md` in sync with reality as the build proceeds.
- Never weaken a grounding rule or the no-fabrication rule for convenience or speed.

## 11. Guardrails: what not to do

- Do not hardcode the schema or assume the document is about a company.
- Do not merge documents into a shared sheet.
- Do not output any value without a supporting source sentence.
- Do not invent data, numbers, sources, or citations.
- Do not generate a chart from fewer than three points or from values that are not comparable.
- Do not use em-dashes or emojis in any output.
- Do not build ahead of the current phase spec.

## 12. Domain glossary

- M&A: mergers and acquisitions.
- Sell-side mandate: advising a company that wants to be sold.
- Buy-side mandate: advising an acquirer looking to buy.
- Target: the company that may be acquired.
- Acquirer: the buyer, which may be a strategic company or a financial sponsor.
- Sponsor: a private equity firm acting as a buyer.
- Deal sourcing: finding and qualifying potential targets, buyers, or deals.
- IOI: indication of interest, an early non-binding signal from a buyer.
- LOI: letter of intent, a later and more serious non-binding agreement on terms.
- CIM: confidential information memorandum, the detailed document used to market a company for sale.
- Comparable transactions, or comps: similar past deals used to inform valuation.
- Valuation multiple: a ratio such as enterprise value to EBITDA used to price a company.
- ARR: annual recurring revenue.
- EBITDA: earnings before interest, taxes, depreciation, and amortization.
- GMV: gross merchandise value.
- Gross margin: revenue minus cost of goods sold, as a percentage of revenue.
- Net revenue retention: revenue retained and expanded from existing customers over a period.

## 13. North star

IB Desk is done when a banker can drop in any research document and get back a sheet that is trustworthy, exhaustive, and well-organized, where every fact is traceable to its source, and that genuinely speeds up understanding a target or a market. Trust comes first. A smaller set of facts that are all correct and all grounded beats a larger set that includes a single invented one.
