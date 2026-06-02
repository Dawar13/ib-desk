"""Bad-input rejection tests for POST /v1/documents. Requires a database.

Each case asserts the ingestion flow rejects invalid input with the expected 4xx
status and a machine-readable detail.code, and never returns a 500. A pass means
validation runs before any storage or insert; a failure means an input case is
mis-classified, returns the wrong status, or leaks an unhandled error as a 500.
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings

pytestmark = pytest.mark.skipif(
    os.environ.get("DATABASE_URL") is None,
    reason="DATABASE_URL is not set; skipping database-backed test",
)


def test_unsupported_type_is_rejected(client: TestClient) -> None:
    response = client.post(
        "/v1/documents",
        files={"file": ("sample.csv", b"a,b,c\n1,2,3\n", "text/csv")},
    )
    assert response.status_code == 415
    assert response.json()["detail"]["code"] == "unsupported_type"


def test_empty_input_is_rejected(client: TestClient) -> None:
    response = client.post("/v1/documents", json={"name": "x", "text": ""})
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "empty_input"


def test_oversized_input_is_rejected(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    # Shrink the limit on the cached settings instance so a tiny payload trips
    # the size guard. monkeypatch restores the original value after the test.
    monkeypatch.setattr(get_settings(), "max_upload_bytes", 10)

    response = client.post(
        "/v1/documents",
        json={"name": "x", "text": "this text is definitely longer than ten bytes"},
    )
    assert response.status_code == 413
    assert response.json()["detail"]["code"] == "file_too_large"
