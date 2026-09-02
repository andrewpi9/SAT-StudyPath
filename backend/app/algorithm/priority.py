"""Priority ranking -- turning mastery estimates into "study this next".

The score for a topic combines three ideas:

    urgency            = 1 - decayed_mastery          how shaky is this skill *now*
    frequency_weight   (given, per section)           how much it's worth on the test
    exploration_bonus  = 0.15 / (1 + attempts_count)  nudge toward blind spots

    priority_score = frequency_weight * urgency + exploration_bonus

``frequency_weight * urgency`` is the expected-points-at-risk term: a wobbly
skill that barely shows up on the test matters less than a wobbly skill that's
everywhere. The exploration bonus is a separate additive term so a topic with no
attempts still surfaces even though we have no evidence it's weak -- you can't
improve what you never diagnose. It decays as ``1/(1+n)``, so it's 0.15 at zero
attempts, 0.075 after one, ~0.03 after four, and quickly becomes negligible.

All pure functions. ``rank_topics`` takes plain ``TopicSnapshot`` values (not ORM
objects) and an explicit ``now`` so the whole engine is testable without a
database or a clock.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime

from app.algorithm.decay import days_since_practice, decayed_mastery
from app.algorithm.mastery import confidence_from_attempts
from app.enums import Section

# Numerator of the exploration bonus: the bonus a never-attempted topic receives.
# Roughly the urgency term of a high-frequency (~0.12) topic sitting at ~0%
# mastery, so an unknown topic ranks alongside a known-bad important one.
EXPLORATION_WEIGHT: float = 0.15


@dataclass(frozen=True)
class TopicSnapshot:
    """Everything the ranker needs about one topic, decoupled from the ORM."""

    topic_id: int
    section: Section
    domain: str
    skill_name: str
    frequency_weight: float
    mastery_score: float
    attempts_count: int
    last_practiced: datetime | None


@dataclass(frozen=True)
class Recommendation:
    """A ranked study-plan entry with its full score breakdown."""

    topic_id: int
    section: Section
    domain: str
    skill_name: str
    frequency_weight: float
    attempts_count: int
    last_practiced: datetime | None
    days_since_practice: int | None
    mastery_score: float
    decayed_mastery: float
    confidence: float
    urgency: float
    exploration_bonus: float
    priority_score: float
    reason: str


def exploration_bonus(attempts_count: int, weight: float = EXPLORATION_WEIGHT) -> float:
    """Additive nudge for under-practised topics: ``weight / (1 + attempts_count)``."""
    return weight / (1 + attempts_count)


def priority_score(
    frequency_weight: float, decayed_mastery_value: float, attempts_count: int
) -> float:
    """``frequency_weight * (1 - decayed_mastery) + exploration_bonus``."""
    urgency = 1.0 - decayed_mastery_value
    return frequency_weight * urgency + exploration_bonus(attempts_count)


def _format_recency(days_elapsed: int | None) -> str:
    if days_elapsed is None:
        return "not practiced yet"
    if days_elapsed == 0:
        return "last practiced today"
    if days_elapsed == 1:
        return "last practiced yesterday"
    return f"last practiced {days_elapsed} days ago"


def build_reason(
    *,
    section: Section,
    frequency_weight: float,
    mastery_score: float,
    decayed_mastery_value: float,
    attempts_count: int,
    days_elapsed: int | None,
) -> str:
    """Human-readable explanation of why a topic is where it is in the plan.

    e.g. ``"Mastery 34% (decayed from 41%) · appears in ~12% of the Reading &
    Writing section · last practiced 9 days ago"``.
    """
    freq_pct = round(frequency_weight * 100)
    freq_part = f"appears in ~{freq_pct}% of the {section.label} section"

    if attempts_count == 0:
        return f"Not yet practiced · {freq_part} · exploration pick"

    earned_pct = round(mastery_score * 100)
    now_pct = round(decayed_mastery_value * 100)
    if now_pct == earned_pct:
        mastery_part = f"Mastery {earned_pct}%"
    else:
        mastery_part = f"Mastery {now_pct}% (decayed from {earned_pct}%)"

    return f"{mastery_part} · {freq_part} · {_format_recency(days_elapsed)}"


def evaluate_topic(snapshot: TopicSnapshot, now: datetime) -> Recommendation:
    """Score a single topic and attach its reason string."""
    elapsed = days_since_practice(snapshot.last_practiced, now)
    decayed = decayed_mastery(snapshot.mastery_score, snapshot.last_practiced, now)
    urgency = 1.0 - decayed
    bonus = exploration_bonus(snapshot.attempts_count)

    return Recommendation(
        topic_id=snapshot.topic_id,
        section=snapshot.section,
        domain=snapshot.domain,
        skill_name=snapshot.skill_name,
        frequency_weight=snapshot.frequency_weight,
        attempts_count=snapshot.attempts_count,
        last_practiced=snapshot.last_practiced,
        days_since_practice=elapsed,
        mastery_score=snapshot.mastery_score,
        decayed_mastery=decayed,
        confidence=confidence_from_attempts(snapshot.attempts_count),
        urgency=urgency,
        exploration_bonus=bonus,
        priority_score=snapshot.frequency_weight * urgency + bonus,
        reason=build_reason(
            section=snapshot.section,
            frequency_weight=snapshot.frequency_weight,
            mastery_score=snapshot.mastery_score,
            decayed_mastery_value=decayed,
            attempts_count=snapshot.attempts_count,
            days_elapsed=elapsed,
        ),
    )


def rank_topics(
    snapshots: Iterable[TopicSnapshot], *, now: datetime, limit: int | None = None
) -> list[Recommendation]:
    """Rank topics for the study plan, most urgent first.

    Sorted by ``priority_score`` descending; ties broken by ``frequency_weight``
    descending (do the higher-value topic first), then by skill name so the
    order is fully deterministic. Returns the top ``limit`` if given, else all.
    """
    ranked = sorted(
        (evaluate_topic(s, now) for s in snapshots),
        key=lambda r: (-r.priority_score, -r.frequency_weight, r.skill_name),
    )
    return ranked if limit is None else ranked[:limit]


def study_plan(
    snapshots: Sequence[TopicSnapshot], *, now: datetime, limit: int = 5
) -> list[Recommendation]:
    """Convenience wrapper: the top ``limit`` recommendations."""
    return rank_topics(snapshots, now=now, limit=limit)
