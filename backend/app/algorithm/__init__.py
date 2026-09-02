"""The recommendation engine: pure, testable functions.

Pipeline:

    update_mastery      per attempt, EWMA -> stored TopicMastery.mastery_score
    decayed_mastery     at read time, forgetting curve -> effective mastery
    rank_topics         priority score + reason strings -> the study plan
    weighted_readiness  frequency-weighted roll-up -> the dashboard headline

No module here imports the ORM or calls ``datetime.now()`` -- callers pass
snapshots and an explicit ``now``. See app/tests/test_mastery_engine.py.
"""

from app.algorithm.decay import DECAY_RATE, days_since_practice, decayed_mastery
from app.algorithm.mastery import (
    COLD_START_MASTERY,
    CONFIDENCE_FULL_AT,
    LEARNING_RATE,
    confidence_from_attempts,
    update_mastery,
)
from app.algorithm.priority import (
    EXPLORATION_WEIGHT,
    Recommendation,
    TopicSnapshot,
    build_reason,
    evaluate_topic,
    exploration_bonus,
    priority_score,
    rank_topics,
    study_plan,
)
from app.algorithm.progress import AttemptEvent, ReadinessPoint, readiness_series
from app.algorithm.readiness import readiness_by_section, weighted_readiness

__all__ = [
    "COLD_START_MASTERY",
    "CONFIDENCE_FULL_AT",
    "DECAY_RATE",
    "EXPLORATION_WEIGHT",
    "LEARNING_RATE",
    "AttemptEvent",
    "ReadinessPoint",
    "Recommendation",
    "TopicSnapshot",
    "readiness_series",
    "build_reason",
    "confidence_from_attempts",
    "days_since_practice",
    "decayed_mastery",
    "evaluate_topic",
    "exploration_bonus",
    "priority_score",
    "rank_topics",
    "readiness_by_section",
    "study_plan",
    "update_mastery",
    "weighted_readiness",
]
