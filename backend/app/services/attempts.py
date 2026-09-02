"""Recording an attempt and folding it into the topic's mastery estimate.

This is the single write path for practice data: both the seed script (replaying
a synthetic history) and ``POST /api/attempts`` go through ``record_attempt`` so
the EWMA update lives in exactly one place.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.algorithm.mastery import (
    COLD_START_MASTERY,
    confidence_from_attempts,
    update_mastery,
)
from app.models.attempt import Attempt
from app.models.enums import Difficulty
from app.models.mastery import TopicMastery
from app.utils.time import utcnow


def _get_or_create_mastery(db: Session, topic_id: int) -> TopicMastery:
    mastery = db.get(TopicMastery, topic_id)
    if mastery is None:
        mastery = TopicMastery(
            topic_id=topic_id,
            mastery_score=COLD_START_MASTERY,
            confidence=0.0,
            attempts_count=0,
            last_practiced=None,
        )
        db.add(mastery)
    return mastery


def record_attempt(
    db: Session,
    *,
    topic_id: int,
    correct: bool,
    time_taken_seconds: int,
    difficulty: Difficulty,
    timestamp: datetime | None = None,
) -> Attempt:
    """Persist one attempt and update its topic's mastery row in place.

    The caller is responsible for committing. When replaying history, feed
    attempts in chronological order so the EWMA reflects the true sequence;
    ``last_practiced`` is guarded so an out-of-order older attempt won't move it
    backwards.
    """
    ts = timestamp or utcnow()

    attempt = Attempt(
        topic_id=topic_id,
        correct=correct,
        time_taken_seconds=time_taken_seconds,
        difficulty=Difficulty(difficulty),
        timestamp=ts,
    )
    db.add(attempt)

    mastery = _get_or_create_mastery(db, topic_id)
    mastery.mastery_score = update_mastery(mastery.mastery_score, correct)
    mastery.attempts_count += 1
    mastery.confidence = confidence_from_attempts(mastery.attempts_count)
    if mastery.last_practiced is None or ts > mastery.last_practiced:
        mastery.last_practiced = ts

    db.flush()
    return attempt
