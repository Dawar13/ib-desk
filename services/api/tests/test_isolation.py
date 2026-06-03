"""Per-visitor isolation test. Requires a real database. Secret-free (paste only).

The headline Phase 5 gate. Workspace A creates a document; workspace B cannot see
it in the list and cannot read its sheet, document, export, events, or original by
id, receiving not found. A pass means each visitor's documents are genuinely
private to them, including against direct access by id. A failure means the one
thing this phase promised, that the person you share with cannot see your
documents and you cannot see theirs, is broken.

Each run uses fresh random workspace ids, so accumulated rows from prior runs do
not interfere, in the same spirit as the other database-backed tests here.
"""

from __future__ import annotations

import os
import uuid

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.skipif(
    os.environ.get("DATABASE_URL") is None,
    reason="DATABASE_URL is not set; skipping database-backed test",
)


def test_documents_are_private_per_workspace(client: TestClient) -> None:
    workspace_a = str(uuid.uuid4())
    workspace_b = str(uuid.uuid4())

    created = client.post(
        "/v1/documents",
        json={
            "name": "A private doc (sample)",
            "text": "Sample isolated content for workspace A only.",
        },
        headers={"X-Workspace-Id": workspace_a},
    )
    assert created.status_code == 201
    body = created.json()
    document_id = body["document_id"]
    sheet_id = body["sheet_id"]

    # A sees its own document in the list; B does not.
    a_list = client.get("/v1/documents", headers={"X-Workspace-Id": workspace_a}).json()
    assert any(item["id"] == document_id for item in a_list)
    b_list = client.get("/v1/documents", headers={"X-Workspace-Id": workspace_b}).json()
    assert all(item["id"] != document_id for item in b_list)

    # B is denied by id on every read path, returning not found rather than leaking.
    assert _status(client, f"/v1/sheets/{sheet_id}", workspace_b) == 404
    assert _status(client, f"/v1/documents/{document_id}", workspace_b) == 404
    # Export, events, and original take the workspace as the ws query parameter,
    # since a download anchor and EventSource cannot set a header.
    assert client.get(f"/v1/sheets/{sheet_id}/export?ws={workspace_b}").status_code == 404
    assert client.get(f"/v1/sheets/{sheet_id}/events?ws={workspace_b}").status_code == 404
    assert client.get(f"/v1/documents/{document_id}/original?ws={workspace_b}").status_code == 404

    # A, the owner, can still read, export, and fetch the original.
    assert _status(client, f"/v1/sheets/{sheet_id}", workspace_a) == 200
    assert client.get(f"/v1/sheets/{sheet_id}/export?ws={workspace_a}").status_code == 200
    assert client.get(f"/v1/documents/{document_id}/original?ws={workspace_a}").status_code == 200


def _status(client: TestClient, path: str, workspace: str) -> int:
    return client.get(path, headers={"X-Workspace-Id": workspace}).status_code
