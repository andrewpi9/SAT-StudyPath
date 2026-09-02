"""Shared pytest fixtures.

The algorithm tests (milestone 2) need no database at all -- they exercise pure
functions. These fixtures are for the service / seed / API layers.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.models import Base


@pytest.fixture
def db() -> Iterator[Session]:
    """A fresh in-memory SQLite database per test."""
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = TestSession()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()
