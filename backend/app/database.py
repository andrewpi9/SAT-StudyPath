"""Database engine, session factory, and schema bootstrap.

For a project this size a full Alembic migration setup is overkill, so the
schema is created with ``Base.metadata.create_all``. Swapping to Postgres is a
matter of changing ``DATABASE_URL``; the SQLite-only ``connect_args`` below is
applied conditionally.
"""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings

_is_sqlite = settings.database_url.startswith("sqlite")

engine: Engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if _is_sqlite else {},
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


if _is_sqlite:

    @event.listens_for(engine, "connect")
    def _enable_sqlite_fks(dbapi_connection, _connection_record) -> None:
        """SQLite ignores ``ON DELETE CASCADE`` unless foreign keys are on."""
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def init_db() -> None:
    """Create any missing tables. Safe to call repeatedly."""
    from app import models  # noqa: F401 - register mappers before create_all

    models.Base.metadata.create_all(bind=engine)


def get_db() -> Iterator[Session]:
    """FastAPI dependency: yield a session and always close it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
