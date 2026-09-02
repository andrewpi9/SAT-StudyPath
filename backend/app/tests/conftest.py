"""Shared pytest fixtures.

The algorithm tests (test_mastery_engine.py) need no database at all -- they
exercise pure functions. These fixtures are for the service / seed / API layers.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.models import Base


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
