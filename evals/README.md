# Evals (placeholder)

This directory is a placeholder. The golden set and the evaluation harness arrive
in Phase 2. Nothing here is wired up yet in Phase 0.

When Phase 2 lands, this directory will hold:

- A golden set of at least eight sample research documents spanning different
  document types (company profile, market overview, deal, person, technology,
  and two messy or ambiguous ones). All golden documents are clearly labeled as
  sample data, not real research.
- The evaluation harness that scores discovery and extraction against
  hand-labeled values, measuring schema sensibleness, field precision and
  recall, grounding faithfulness, fabrication rate, and schema stability.
- The CI wiring that runs these evals so any prompt change must pass the bar
  before merge.

See BUILD_PLAN.md, the Evaluation section and Phase 2, for the full plan. Until
then, this is intentionally empty apart from this note and a .gitkeep file.
