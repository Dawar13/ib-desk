"""Health endpoint test. Requires a real database connection.

A pass means GET /health performed a real SELECT 1, found the database
connected, and reported status ok for the ib-desk-api service. A failure means
either the database was unreachable while DATABASE_URL was set, or the health
contract changed.
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.skipif(
    os.environ.get("DATABASE_URL") is None,
    reason="DATABASE_URL is not set; skipping database-backed test",
)


def test_health_reports_connected(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["database"] == "connected"
    assert body["status"] == "ok"
    assert body["service"] == "ib-desk-api"
