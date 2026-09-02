"""Time helpers.

The whole app stores and compares timestamps as *naive UTC* datetimes. SQLite
does not preserve timezone information, so mixing aware and naive datetimes is a
classic source of ``TypeError: can't subtract offset-naive and offset-aware``
bugs. Standardising on naive UTC everywhere avoids that and still ports cleanly
to Postgres (store as ``timestamp`` / ``timestamptz`` at the DB layer).
"""

from __future__ import annotations

from datetime import datetime, timezone


def utcnow() -> datetime:
    """Current UTC time as a naive ``datetime`` (no tzinfo)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def days_between(earlier: datetime, later: datetime) -> float:
    """Fractional days from ``earlier`` to ``later`` (negative if reversed)."""
    return (later - earlier).total_seconds() / 86_400.0
