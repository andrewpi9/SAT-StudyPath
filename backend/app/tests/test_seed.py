"""The seed script must produce a believable, deterministic demo history."""

from __future__ import annotations

import random

from sqlalchemy import func, select

from app.algorithm.mastery import COLD_START_MASTERY, confidence_from_attempts, update_mastery
from app.models.attempt import Attempt
from app.models.mastery import TopicMastery
from app.models.topic import Topic
from app.services.seeding import generate_history, seed_database
from app.services.topics import load_taxonomy
from app.services.users import get_or_create_demo_user


def _seed(db, *, rng_seed: int = 42, attempts: int | None = None) -> tuple[int, int]:
    """Load the taxonomy, generate a history for a fresh demo user, return
    ``(user_id, attempt_count)``."""
    load_taxonomy(db)
    user = get_or_create_demo_user(db)
    db.flush()
    count = generate_history(db, user.id, random.Random(rng_seed), target_attempts=attempts)
    db.commit()
    return user.id, count


def test_generates_attempts_in_expected_range(db) -> None:
    _, count = _seed(db)
    assert 150 <= count <= 250
    assert db.scalar(select(func.count(Attempt.id))) == count


def test_history_is_deterministic_for_a_given_seed(db) -> None:
    user_id, count_a = _seed(db)
    signature_a = [
        (a.topic_id, a.correct, a.time_taken_seconds)
        for a in db.scalars(select(Attempt).order_by(Attempt.timestamp, Attempt.id))
    ]

    for row in db.scalars(select(Attempt)):
        db.delete(row)
    for row in db.scalars(select(TopicMastery)):
        db.delete(row)
    db.commit()

    count_b = generate_history(db, user_id, random.Random(42))
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
    topic_count = db.scalar(select(func.count(Topic.id)))

    practised = [m for m in masteries if m.attempts_count > 0]
    barely = [m for m in masteries if 0 < m.attempts_count <= 3]

    # One topic is never attempted -> it has no mastery row at all.
    assert len(masteries) == topic_count - 1
    assert len(barely) >= 2

    strong = [m for m in practised if m.mastery_score >= 0.75]
    weak = [m for m in practised if m.mastery_score <= 0.45]
    assert strong and weak, "the demo needs a visible spread of mastery"


def test_mastery_matches_a_chronological_replay(db) -> None:
    """Stored mastery must equal an EWMA replay of that topic's attempts in order."""
    user_id, _ = _seed(db)
    mastery_row = db.scalars(
        select(TopicMastery).where(TopicMastery.attempts_count >= 5).limit(1)
    ).first()
    assert mastery_row is not None

    attempts = list(
        db.scalars(
            select(Attempt)
            .where(Attempt.topic_id == mastery_row.topic_id, Attempt.user_id == user_id)
            .order_by(Attempt.timestamp, Attempt.id)
        )
    )
    expected = COLD_START_MASTERY
    for attempt in attempts:
        expected = update_mastery(expected, attempt.correct)

    assert mastery_row.mastery_score == expected
    assert mastery_row.attempts_count == len(attempts)
    assert mastery_row.confidence == confidence_from_attempts(len(attempts))
    assert mastery_row.last_practiced == max(a.timestamp for a in attempts)


def test_attempts_scale_with_target(db) -> None:
    _, count = _seed(db, attempts=400)
    assert 320 <= count <= 480  # scaling is approximate (per-topic rounding)


def test_seed_database_is_reproducible_and_per_user(db) -> None:
    user = get_or_create_demo_user(db)
    db.flush()

    first = seed_database(db, user_id=user.id, rng_seed=42)
    assert first.topics_created == 35
    assert 150 <= first.attempts_created <= 250

    second = seed_database(db, user_id=user.id, rng_seed=42)  # reset_user wipes + regenerates
    assert second.attempts_created == first.attempts_created
    assert db.scalar(select(func.count(Attempt.id))) == second.attempts_created
    assert db.scalar(select(func.count(Topic.id))) == 35
