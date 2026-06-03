-- IB Desk migration 0003: per-visitor workspace scoping (Phase 5).
--
-- Phase 5 gives each visitor a private document space without a login, keyed by
-- an anonymous workspace id the browser generates and sends on every request.
-- documents already carries workspace_id; this tags sheets with the same id so a
-- sheet read can be scoped and verified directly, without joining through its
-- document on every request. Existing sheets are backfilled from their document.
--
-- This is isolation, not authentication: the id lives in the browser and the
-- protection rests on it being long and random. It is the right level for a
-- trusted person looking at public research, not for real client documents.
--
-- Idempotent so the migration runner can apply it safely more than once.

alter table sheets add column if not exists workspace_id uuid;

update sheets s
set workspace_id = d.workspace_id
from documents d
where d.id = s.document_id and s.workspace_id is null;

create index if not exists sheets_workspace_id_idx on sheets (workspace_id);
create index if not exists documents_workspace_id_idx on documents (workspace_id);
