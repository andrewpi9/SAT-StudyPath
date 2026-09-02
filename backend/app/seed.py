"""Seed the database with the taxonomy and a synthetic practice history.

Run from the ``backend/`` directory:

    python -m app.seed                # deterministic demo history (rng seed 42)
    python -m app.seed --seed 7       # a different but still reproducible history
    python -m app.seed --attempts 300 # scale the number of attempts
    python -m app.seed --keep         # don't wipe existing data first

The generated history is intentionally uneven: a handful of topics are strong,
several are weak, a few are barely touched, and one has never been attempted --
so the dashboard and the study plan both look meaningful on first run without
anyone grinding real practice questions.

Every attempt is pure metadata (topic tag, correct/incorrect, seconds,
difficulty, timestamp). No question text, answer choices, or passages exist
anywhere in this project.
"""

from __future__ import annotations

import argparse
import random
from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.algorithm.decay import decayed_mastery
from app.algorithm.priority import TopicSnapshot, rank_topics
from app.algorithm.readiness import readiness_by_section, weighted_readiness
from app.database import SessionLocal, engine
from app.enums import Difficulty, Section
from app.models import Base
from app.models.mastery import TopicMastery
from app.models.topic import Topic
from app.services.attempts import record_attempt
from app.services.topics import load_taxonomy
from app.utils.time import utcnow

# ---------------------------------------------------------------------------
# Synthetic-student profiles
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Profile:
    name: str
    # Number of topics that get this profile (across the 35-skill taxonomy).
    topic_count: int
    # Underlying "true" probability the student answers a medium question right.
    true_p_range: tuple[float, float]
    # Number of attempts logged against a topic with this profile.
    attempts_range: tuple[int, int]
    # Chance this topic's most recent practice was a while ago (-> visible decay).
    stale_chance: float
    # Difficulty mix (easy, medium, hard) the student practised at.
    difficulty_mix: tuple[float, float, float]


# topic_count values sum to the 35-skill taxonomy. The synthetic student has
# worked through most topics at least once (so the study plan is driven by
# decay + frequency + urgency, the interesting part), with a few barely-touched
# and one never-touched topic so the exploration bonus visibly matters too.
PROFILES: list[Profile] = [
    Profile("strong", 7, (0.80, 0.95), (5, 11), 0.42, (0.25, 0.45, 0.30)),
    Profile("developing", 13, (0.52, 0.72), (5, 10), 0.34, (0.33, 0.47, 0.20)),
    Profile("weak", 11, (0.18, 0.45), (4, 9), 0.30, (0.45, 0.42, 0.13)),
    Profile("barely_touched", 3, (0.30, 0.65), (2, 3), 0.15, (0.55, 0.37, 0.08)),
    Profile("untouched", 1, (0.30, 0.65), (0, 0), 0.0, (0.5, 0.4, 0.1)),
]

# Accuracy shift applied on top of ``true_p`` for each difficulty band.
_DIFFICULTY_ACCURACY_SHIFT = {
    Difficulty.EASY: 0.12,
    Difficulty.MEDIUM: 0.0,
    Difficulty.HARD: -0.16,
}

# Typical seconds spent per difficulty band (before per-attempt noise).
_DIFFICULTY_BASE_SECONDS = {
    Difficulty.EASY: 32,
    Difficulty.MEDIUM: 58,
    Difficulty.HARD: 92,
}

_HISTORY_WINDOW_DAYS = 26  # attempts are spread across roughly the last 3-4 weeks


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _pick_difficulty(rng: random.Random, mix: tuple[float, float, float]) -> Difficulty:
    return rng.choices([Difficulty.EASY, Difficulty.MEDIUM, Difficulty.HARD], weights=mix, k=1)[0]


def _attempt_time_seconds(rng: random.Random, difficulty: Difficulty, correct: bool) -> int:
    base = _DIFFICULTY_BASE_SECONDS[difficulty]
    seconds = base + rng.gauss(0, base * 0.22)
    if not correct:
        # A wrong answer is either a fast guess or a slow struggle.
        seconds += rng.choice([-base * 0.35, base * 0.45])
    return int(_clamp(seconds, 8, 240))


@dataclass
class _PlannedAttempt:
    topic_id: int
    correct: bool
    time_taken_seconds: int
    difficulty: Difficulty
    days_ago: float


def _plan_topic_attempts(
    rng: random.Random, topic: Topic, profile: Profile, count: int
) -> list[_PlannedAttempt]:
    """Generate ``count`` attempts for one topic, clustered in a practice window."""
    true_p = rng.uniform(*profile.true_p_range)

    if rng.random() < profile.stale_chance:
        recency_days = rng.uniform(9.0, 20.0)  # last practised a while back
    else:
        recency_days = rng.uniform(0.4, 6.0)  # practised recently
    span_days = rng.uniform(5.0, 16.0)

    planned: list[_PlannedAttempt] = []
    for _ in range(count):
        difficulty = _pick_difficulty(rng, profile.difficulty_mix)
        p_correct = _clamp(
            true_p + _DIFFICULTY_ACCURACY_SHIFT[difficulty] + rng.gauss(0, 0.05), 0.03, 0.98
        )
        correct = rng.random() < p_correct
        planned.append(
            _PlannedAttempt(
                topic_id=topic.id,
                correct=correct,
                time_taken_seconds=_attempt_time_seconds(rng, difficulty, correct),
                difficulty=difficulty,
                days_ago=_clamp(
                    recency_days + rng.uniform(0.0, span_days), 0.1, _HISTORY_WINDOW_DAYS
                ),
            )
        )
    return planned


def generate_history(db: Session, rng: random.Random, target_attempts: int | None = None) -> int:
    """Assign a profile to every topic and replay a synthetic attempt history.

    Attempts are replayed in strict chronological order so each topic's EWMA
    mastery reflects the real sequence of outcomes. Returns the number of
    attempts created.
    """
    topics = list(db.scalars(select(Topic).order_by(Topic.id)))
    rng.shuffle(topics)

    # Slice the shuffled topic list into profile buckets.
    assignments: list[tuple[Topic, Profile]] = []
    cursor = 0
    for profile in PROFILES:
        for topic in topics[cursor : cursor + profile.topic_count]:
            assignments.append((topic, profile))
        cursor += profile.topic_count
    for topic in topics[cursor:]:  # any remainder -> developing
        assignments.append((topic, PROFILES[1]))

    planned_counts = {
        topic.id: rng.randint(*profile.attempts_range) for topic, profile in assignments
    }

    if target_attempts is not None:
        current_total = sum(planned_counts.values()) or 1
        scale = target_attempts / current_total
        planned_counts = {
            tid: (max(1, round(n * scale)) if n > 0 else 0) for tid, n in planned_counts.items()
        }

    all_planned: list[_PlannedAttempt] = []
    for topic, profile in assignments:
        count = planned_counts[topic.id]
        if count > 0:
            all_planned.extend(_plan_topic_attempts(rng, topic, profile, count))

    now = utcnow()
    all_planned.sort(key=lambda a: a.days_ago, reverse=True)  # oldest first
    for plan in all_planned:
        record_attempt(
            db,
            topic_id=plan.topic_id,
            correct=plan.correct,
            time_taken_seconds=plan.time_taken_seconds,
            difficulty=plan.difficulty,
            timestamp=now - timedelta(days=plan.days_ago),
        )

    return len(all_planned)


def reset_database() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def _snapshots(db: Session) -> list[TopicSnapshot]:
    """Project the ORM state into the algorithm's plain input type."""
    topics = db.scalars(select(Topic)).all()
    return [
        TopicSnapshot(
            topic_id=t.id,
            section=t.section,
            domain=t.domain,
            skill_name=t.skill_name,
            frequency_weight=t.frequency_weight,
            mastery_score=t.mastery.mastery_score,
            attempts_count=t.mastery.attempts_count,
            last_practiced=t.mastery.last_practiced,
        )
        for t in topics
    ]


def print_summary(db: Session) -> None:
    now = utcnow()
    topics = list(
        db.scalars(
            select(Topic).order_by(
                Topic.section, Topic.domain, Topic.frequency_weight.desc(), Topic.skill_name
            )
        )
    )
    total_attempts = sum(t.mastery.attempts_count for t in topics if t.mastery)
    snapshots = _snapshots(db)
    by_section = readiness_by_section(snapshots, now)

    print(f"\n  {len(topics)} topics · {total_attempts} synthetic attempts\n")
    for section in (Section.MATH, Section.READING_WRITING):
        section_topics = [t for t in topics if t.section == section]
        print(f"  ══ {section.label} " + "═" * (70 - len(section.label)))
        current_domain = ""
        for topic in section_topics:
            if topic.domain != current_domain:
                current_domain = topic.domain
                print(f"  {current_domain}")
            m: TopicMastery = topic.mastery
            decayed = decayed_mastery(m.mastery_score, m.last_practiced, now)
            if m.last_practiced is None:
                last, shown = "never", "  --  "
            else:
                last = f"{(now - m.last_practiced).days}d ago"
                shown = f"{m.mastery_score * 100:3.0f}% → {decayed * 100:3.0f}%"
            print(f"    {topic.skill_name:<54}{m.attempts_count:>3} att{shown:>14}{last:>9}")

        print(f"    → readiness (frequency-weighted, decayed): {by_section[section] * 100:.0f}%\n")

    print(f"  Overall readiness: {weighted_readiness(snapshots, now) * 100:.0f}%\n")
    print("  ── Today's study plan (top 5) " + "─" * 43)
    for i, rec in enumerate(rank_topics(snapshots, now=now, limit=5), start=1):
        print(f"  {i}. {rec.skill_name}")
        print(f"     {rec.reason}")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed SAT StudyPath with synthetic data.")
    parser.add_argument("--seed", type=int, default=42, help="RNG seed (default: 42)")
    parser.add_argument(
        "--attempts", type=int, default=None, help="approx. total attempts to generate"
    )
    parser.add_argument(
        "--keep", action="store_true", help="keep existing data instead of wiping it"
    )
    args = parser.parse_args()

    if not args.keep:
        reset_database()
    else:
        Base.metadata.create_all(bind=engine)

    rng = random.Random(args.seed)
    db = SessionLocal()
    try:
        created = load_taxonomy(db)
        print(f"Loaded taxonomy: {len(created)} topics inserted.")
        attempts = generate_history(db, rng, target_attempts=args.attempts)
        db.commit()
        print(f"Generated {attempts} synthetic attempts (rng seed {args.seed}).")
        print_summary(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
