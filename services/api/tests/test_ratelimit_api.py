"""Rate limiting at the endpoint, DB-gated and secret-free.

Hammering the upload and extract endpoints beyond the configured limit is
throttled with a clear 429, not a crash and not unbounded model cost. A pass
means the public link cannot be abused to run up the bill or flood the service.
A failure is cost or availability exposure.

The limiter state is reset before each test by the autouse fixture in conftest,
and each test uses a fresh workspace id, so the counts are isolated.
"""

from __future__ import annotations

import os
import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient

import app.routes as routes
from app.config import get_settings

pytestmark = pytest.mark.skipif(
    os.environ.get("DATABASE_URL") is None,
    reason="DATABASE_URL is not set; skipping database-backed test",
)


def test_upload_is_rate_limited(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(get_settings(), "rate_limit_upload_max", 3)
    headers = {"X-Workspace-Id": str(uuid.uuid4())}

    def upload(n: int) -> Any:
        return client.post(
            "/v1/documents",
            json={"name": f"doc {n} (sample)", "text": f"Sample upload content {n}."},
            headers=headers,
        )

    assert upload(1).status_code == 201
    assert upload(2).status_code == 201
    assert upload(3).status_code == 201
    throttled = upload(4)
    assert throttled.status_code == 429
    assert "detail" in throttled.json()


def test_extract_is_rate_limited(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(get_settings(), "rate_limit_extract_max", 2)

    # Make extraction a no-op so the burst test starts no real background work.
    async def _noop(*_args: Any, **_kwargs: Any) -> None:
        return None

    monkeypatch.setattr(routes, "run_extraction", _noop)

    headers = {"X-Workspace-Id": str(uuid.uuid4())}
    created = client.post(
        "/v1/documents",
        json={"name": "to extract (sample)", "text": "Sample content to extract."},
        headers=headers,
    )
    sheet_id = created.json()["sheet_id"]

    assert client.post(f"/v1/sheets/{sheet_id}/extract", headers=headers).status_code == 202
    assert client.post(f"/v1/sheets/{sheet_id}/extract", headers=headers).status_code == 202
    assert client.post(f"/v1/sheets/{sheet_id}/extract", headers=headers).status_code == 429
