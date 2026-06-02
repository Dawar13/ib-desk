# Evals: the label-free Phase 2 check

This is the label-free evaluation harness for Phase 2, the schema-agnostic
extraction engine. The owner deliberately declined the hand-labeled golden set
described in the original BUILD_PLAN.md evaluation section, so the precision and
recall and schema-sensibleness metrics that need human labels are out of scope
here. This harness measures only what can be computed without any labeling, by
running the live pipeline over a small set of clearly-labeled sample documents.

## What it measures

- Grounding resolution: the share of emitted cells whose stored character span
  maps back to the supporting sentence in the source text, and whose supporting
  sentence is independently locatable by the same search the engine uses. By
  construction this is expected to be 1.0, because the engine drops any value
  whose quote it cannot locate and computes the span itself.
- Fabrication rate: 1 minus grounding resolution. Expected near zero. This is the
  cardinal metric. A single ungrounded value is a fabrication and fails the gate.
- Value-level stability: each document is run a fixed number of times (default 3)
  and the harness reports the share of (section_key, row_idx, col_key) values
  whose normalized value (value_norm) is identical across every run. This checks
  content determinism at the value level, not section ordering or positioning.

There is no labeled golden set and no precision, recall, or schema-sensibleness
score here. Those require hand labeling that the owner descoped.

## Sample documents

The documents under `evals/docs/` are fictional sample data, clearly labeled as
sample inside each file. They contain invented company names, people, investors,
and figures written as plain prose so the engine can discover sections and ground
values. They are not real research and must never be presented as real.

## How to run

This harness runs live against OpenAI. It does not use cassette replay, so it
needs a real API key and the per-pass model names set. It also needs a database
to persist and read back the sections and cells.

Set the following environment variables:

- `DATABASE_URL`: a Postgres connection string the harness can write to and read
  back from. It creates and then deletes its own temporary documents and sheets.
- `LLM_MODE=live`
- `OPENAI_API_KEY`: your OpenAI key. Never commit this.
- `OPENAI_MODEL_DISCOVERY`, `OPENAI_MODEL_EXTRACTION`, `OPENAI_MODEL_VERIFICATION`:
  the per-pass model identifiers.

Optional:

- `EVAL_STABILITY_RUNS`: how many times to run each document for the stability
  metric (default 3).
- `EVAL_FABRICATION_THRESHOLD`: the maximum allowed fabrication rate before the
  harness exits non-zero (default 0.01).

Run it from the service directory so the app modules import cleanly:

```
cd services/api
uv run python ../../evals/run_eval.py
```

The harness prints a per-document and aggregate summary and writes
`evals/report.json`. It exits non-zero if the fabrication rate exceeds the
threshold, so it can gate. If `LLM_MODE` is not `live`, or the key or any per-pass
model is missing, it prints a clear message and exits non-zero without calling the
model or touching the database.

## Targets

- Fabrication rate: near zero. The gate fails above `EVAL_FABRICATION_THRESHOLD`
  (default 0.01).
- Grounding resolution: 1.0 (100 percent) by construction, since the engine drops
  any value it cannot ground and computes the span itself.
- Value-level stability: high. A model at low temperature is near-deterministic,
  not perfectly guaranteed, so this is reported rather than hard-gated here.
