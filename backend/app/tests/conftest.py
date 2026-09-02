"""Shared pytest fixtures.

The algorithm tests (test_mastery_engine.py) need no database at all -- they
exercise pure functions. These fixtures are for the service / seed / API layers.
"""

from __future__ import annotations

import os

# Fast, deterministic auth in tests. Must be set before app.config is imported.
os.environ.setdefault("BCRYPT_ROUNDS", "4")
os.environ.setdefault("JWT_SECRET", "test-secret")

from collections.abc import Iterator  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.models import Base  # noqa: E402

TEST_EMAIL = "test@studypath.app"
TEST_PASSWORD = "password123"


@pytest.fixture
def db() -> Iterator[Session]:
    """A fresh in-memory SQLite database per test.

    StaticPool keeps every connection pointed at the same in-memory database, so
    the session and anything else sharing the engine see the same tables.
    """
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = TestSession()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def client(db: Session) -> Iterator[TestClient]:
    """A TestClient whose requests run against the in-memory ``db`` session.

    Constructed without a ``with`` block so the app lifespan (which would call
    ``init_db()`` on the real engine) never fires.
    """
    from app.database import get_db
    from app.main import app

    app.dependency_overrides[get_db] = lambda: db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def user_id(client: TestClient) -> int:
    """Sign up a test user via the API and return its id."""
    resp = client.post("/api/auth/signup", json={"email": TEST_EMAIL, "password": TEST_PASSWORD})
    assert resp.status_code == 201, resp.text
    return resp.json()["user"]["id"]


@pytest.fixture
def authed_client(client: TestClient, user_id: int) -> TestClient:
    """A TestClient with a valid Bearer token for the test user set as a default
    header on every request."""
    token = client.post(
        "/api/auth/login", json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
    ).json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"
    return client
