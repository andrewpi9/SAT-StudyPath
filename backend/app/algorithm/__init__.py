"""The recommendation engine: pure, testable functions.

Milestone 1 ships the EWMA mastery update (``mastery``). Milestone 2 adds
forgetting-curve decay and priority ranking alongside their pytest suite.
"""

from app.algorithm.mastery import (
    COLD_START_MASTERY,
    CONFIDENCE_FULL_AT,
    LEARNING_RATE,
    confidence_from_attempts,
    update_mastery,
)

__all__ = [
    "COLD_START_MASTERY",
    "CONFIDENCE_FULL_AT",
    "LEARNING_RATE",
    "confidence_from_attempts",
    "update_mastery",
]
