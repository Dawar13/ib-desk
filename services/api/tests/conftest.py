"""Shared test fixtures and the database skip marker for the API tests.

The client fixture wraps TestClient in a with-block so the FastAPI lifespan runs
(opening the pool when DATABASE_URL is set, and closing it on teardown). Tests
that need a real database apply a module-level pytestmark skipif on
os.environ.get("DATABASE_URL"); the same condition is exported here as
requires_db for convenience.
"""

from __future__ import annotations

import os
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.main import app

DB_URL: str | None = os.environ.get("DATABASE_URL")

# Reusable skip marker for tests that require a real database connection.
requires_db = pytest.mark.skipif(
    DB_URL is None,
    reason="DATABASE_URL is not set; skipping tests that require a database",
)


@pytest.fixture(scope="session")
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def _reset_rate_limits() -> Iterator[None]:
    # Clear the in-process rate-limiter state before each test, so bursts in one
    # test do not throttle another and the suite stays order-independent.
    from app.routes import reset_rate_limits

    reset_rate_limits()
    yield
