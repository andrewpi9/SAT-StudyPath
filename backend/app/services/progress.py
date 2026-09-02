"""Build one user's readiness-over-time series from the database."""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.algorithm.progress import AttemptEvent, ReadinessPoint, readiness_series
from app.enums import Section
from app.models.attempt import Attempt
from app.models.topic import Topic
from app.utils.time import utcnow

MAX_RANGE_DAYS = 365


def get_readiness_series(db: Session, user_id: int, days: int) -> list[ReadinessPoint]:
    days = max(1, min(days, MAX_RANGE_DAYS))
    end = utcnow().date()
    start = end - timedelta(days=days - 1)

    topic_weights: dict[int, tuple[Section, float]] = {
        t.id: (t.section, t.frequency_weight) for t in db.scalars(select(Topic))
    }
    events = [
        AttemptEvent(topic_id=a.topic_id, correct=a.correct, at=a.timestamp)
        for a in db.scalars(
            select(Attempt).where(Attempt.user_id == user_id).order_by(Attempt.timestamp)
        )
    ]
    return readiness_series(topic_weights, events, start=start, end=end)
