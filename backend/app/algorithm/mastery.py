"""Mastery update: exponentially weighted moving average (EWMA).

Why EWMA and not plain accuracy? A student's skill *changes over time* -- that's
the entire point of studying. A running average of every attempt they've ever
made would let a rough first week permanently drag down a topic they've since
nailed. EWMA answers a more useful question: "given how they've been doing
*lately*, how well do they know this?"

Each attempt nudges the estimate a fixed fraction (``LEARNING_RATE``) of the way
toward that attempt's outcome (1.0 correct, 0.0 wrong). The influence of any one
attempt therefore decays geometrically as newer attempts arrive, so recent
performance dominates without old attempts being thrown away entirely.

These functions are pure and side-effect free so the algorithm can be unit
tested against hand-computed numbers, independent of the database or API.
"""

from __future__ import annotations

# Fraction of the gap between the current estimate and the latest outcome that a
# single attempt closes. 0.3 means one attempt moves the estimate 30% of the way
# to that result; the previous estimate keeps the other 70%. Higher = more
# reactive/noisier, lower = smoother/slower. 0.3 is a deliberate middle ground:
# ~3 consistent attempts to move the estimate most of the way.
LEARNING_RATE: float = 0.3

# Cold-start mastery for a topic with zero attempts. Set slightly below the 0.5
# midpoint: with no evidence, assume *not yet competent* rather than neutral.
COLD_START_MASTERY: float = 0.4

# Attempts at which confidence in the estimate reaches its ceiling of 1.0.
CONFIDENCE_FULL_AT: int = 5


def update_mastery(
    old_mastery: float, correct: bool, learning_rate: float = LEARNING_RATE
) -> float:
    """Return the new mastery estimate after one attempt.

    ``new = old + lr * (outcome - old)``, the standard EWMA / delta-rule update.
    The result stays within [0, 1] as long as ``old`` is in [0, 1] and
    ``learning_rate`` is in [0, 1], so no clamping is needed.

    Args:
        old_mastery: Current estimate in [0, 1].
        correct: Whether the latest attempt was correct.
        learning_rate: Step size in [0, 1]; defaults to ``LEARNING_RATE``.
    """
    outcome = 1.0 if correct else 0.0
    return old_mastery + learning_rate * (outcome - old_mastery)


def confidence_from_attempts(attempts_count: int, full_at: int = CONFIDENCE_FULL_AT) -> float:
    """How much to trust the mastery estimate, in [0, 1].

    Grows linearly with the number of attempts and saturates at 1.0 once there
    are ``full_at`` of them. One correct answer shouldn't look as certain as ten;
    this is what lets the UI show "34% (low confidence)" for a barely-touched
    topic. It does not feed the mastery number itself -- only its presentation
    and, indirectly, the exploration bonus in the ranking step.
    """
    if attempts_count <= 0:
        return 0.0
    return min(1.0, attempts_count / full_at)
