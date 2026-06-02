-- IB Desk migration 0002: document ingestion metadata (Phase 1).
--
-- Captures page metadata at ingestion: the page count and the per-page character
-- offsets into documents.raw_text. This is cheap to record now and expensive to
-- reconstruct later, and it lets a later phase map a grounded character span back
-- to its source page. Both columns are nullable: page_count is null for pasted
-- text where pages do not apply, and page_offsets holds one offset per page.
--
-- Idempotent so the migration runner can apply it safely more than once.

alter table documents add column if not exists page_count int;
alter table documents add column if not exists page_offsets jsonb;
