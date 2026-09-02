"""The seed script must produce a believable, deterministic demo history."""

from __future__ import annotations

import random

from sqlalchemy import func, select

from app.algorithm.mastery import COLD_START_MASTERY
from app.models.attempt import Attempt
from app.models.mastery import TopicMastery
from app.models.topic import Topic
from app.seed import generate_history
from app.services.topics import load_taxonomy


def _seed(db, *, rng_seed: int = 42, attempts: int | None = None) -> int:
    load_taxonomy(db)
    count = generate_history(db, random.Random(rng_seed), target_attempts=attempts)
    db.commit()
    return count


def test_generates_attempts_in_expected_range(db) -> None:
    count = _seed(db)
    assert 150 <= count <= 250
    assert db.scalar(select(func.count(Attempt.id))) == count


def test_history_is_deterministic_for_a_given_seed(db) -> None:
    count_a = _seed(db)
    signature_a = [
        (a.topic_id, a.correct, a.time_taken_seconds)
        for a in db.scalars(select(Attempt).order_by(Attempt.timestamp, Attempt.id))
    ]

    for row in db.scalars(select(Attempt)):
        db.delete(row)
    for row in db.scalars(select(TopicMastery)):
        db.delete(row)
    db.commit()

    count_b = generate_history(db, random.Random(42))
    db.commit()
    signature_b = [
        (a.topic_id, a.correct, a.time_taken_seconds)
        for a in db.scalars(select(Attempt).order_by(Attempt.timestamp, Attempt.id))
    ]
    assert count_a == count_b
    assert signature_a == signature_b


def test_history_is_uneven_some_strong_some_weak_some_barely_touched(db) -> None:
    _seed(db)
    masteries = list(db.scalars(select(TopicMastery)))

    untouched = [m for m in masteries if m.attempts_count == 0]
    barely = [m for m in masteries if 0 < m.attempts_count <= 3]
    practised = [m for m in masteries if m.attempts_count > 0]

    # At least one never-attempted topic (exercises the exploration bonus in the
    # live demo) and a few barely-touched ones.
    assert len(untouched) >= 1
    assert all(m.mastery_score == COLD_START_MASTERY for m in untouched)
    assert all(m.last_practiced is None for m in untouched)
    assert len(barely) >= 2

    strong = [m for m in practised if m.mastery_score >= 0.75]
    weak = [m for m in practised if m.mastery_score <= 0.45]
    assert strong and weak, "the demo needs a visible spread of mastery"


def test_mastery_matches_a_chronological_replay(db) -> None:
    """Stored mastery must equal an EWMA replay of that topic's attempts in order."""
    from app.algorithm.mastery import confidence_from_attempts, update_mastery

    _seed(db)
    topic_with_history = db.scalars(
        select(Topic).join(TopicMastery).where(TopicMastery.attempts_count >= 5).limit(1)
    ).first()
    assert topic_with_history is not None

    attempts = list(
        db.scalars(
            select(Attempt)
            .where(Attempt.topic_id == topic_with_history.id)
            .order_by(Attempt.timestamp, Attempt.id)
        )
    )
    expected = COLD_START_MASTERY
    for attempt in attempts:
        expected = update_mastery(expected, attempt.correct)

    mastery = db.get(TopicMastery, topic_with_history.id)
    assert mastery.mastery_score == expected
    assert mastery.attempts_count == len(attempts)
    assert mastery.confidence == confidence_from_attempts(len(attempts))
    assert mastery.last_practiced == max(a.timestamp for a in attempts)


def test_attempts_scale_with_target(db) -> None:
    count = _seed(db, attempts=400)
    assert 320 <= count <= 480  # scaling is approximate (per-topic rounding)
