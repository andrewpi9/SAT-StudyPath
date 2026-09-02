"""Readiness over time — reconstructed from the attempt history.

Nothing is stored for this. Given every attempt (topic, outcome, timestamp) and
each topic's frequency weight, we replay the EWMA forward and snapshot the
frequency-weighted, decay-adjusted readiness at the end of each day in the
requested window. O(attempts + days).

The "as of day D" readiness applies decay *to day D* — so a flat stretch in the
chart during a study break is the forgetting curve pulling against no new
practice, which is the behaviour worth seeing.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from app.algorithm.decay import decayed_mastery
from app.algorithm.mastery import COLD_START_MASTERY, update_mastery
from app.enums import Section


@dataclass(frozen=True)
class AttemptEvent:
    topic_id: int
    correct: bool
    at: datetime


@dataclass(frozen=True)
class ReadinessPoint:
    day: date
    overall: float
    by_section: dict[Section, float]


@dataclass
class _TopicState:
    section: Section
    frequency_weight: float
    mastery: float = COLD_START_MASTERY
    last_practiced: datetime | None = None


def readiness_series(
    topic_weights: Mapping[int, tuple[Section, float]],
    events: Sequence[AttemptEvent],
    *,
    start: date,
    end: date,
) -> list[ReadinessPoint]:
    """One readiness point per day from ``start`` to ``end`` inclusive."""
    state = {
        topic_id: _TopicState(section, weight)
        for topic_id, (section, weight) in topic_weights.items()
    }
    ordered = sorted(events, key=lambda e: e.at)
    cursor = 0
    points: list[ReadinessPoint] = []

    day = start
    while day <= end:
        cutoff = datetime.combine(day, time.max)
        while cursor < len(ordered) and ordered[cursor].at <= cutoff:
            event = ordered[cursor]
            topic = state.get(event.topic_id)
            if topic is not None:
                topic.mastery = update_mastery(topic.mastery, event.correct)
                if topic.last_practiced is None or event.at > topic.last_practiced:
                    topic.last_practiced = event.at
            cursor += 1
        points.append(_snapshot(day, cutoff, state.values()))
        day += timedelta(days=1)

    return points


def _snapshot(day: date, at: datetime, topics: Sequence[_TopicState]) -> ReadinessPoint:
    section_earned: dict[Section, float] = {}
    section_weight: dict[Section, float] = {}
    for topic in topics:
        eff = decayed_mastery(topic.mastery, topic.last_practiced, at)
        section_earned[topic.section] = section_earned.get(topic.section, 0.0) + (
            topic.frequency_weight * eff
        )
        section_weight[topic.section] = (
            section_weight.get(topic.section, 0.0) + topic.frequency_weight
        )

    by_section = {
        section: section_earned[section] / section_weight[section]
        for section in section_weight
        if section_weight[section] > 0
    }
    total_weight = sum(section_weight.values())
    overall = sum(section_earned.values()) / total_weight if total_weight else 0.0
    return ReadinessPoint(day=day, overall=overall, by_section=by_section)
