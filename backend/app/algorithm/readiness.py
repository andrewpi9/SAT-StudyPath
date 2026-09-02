"""Overall "test readiness" -- one number summarising where the student stands.

A frequency-weighted average of every topic's *decayed* mastery. Weighting by
``frequency_weight`` means being shaky on a skill that's all over the test drags
the number down more than being shaky on a rare one -- it approximates "what
fraction of the points on offer can you currently expect to get".

Used for the dashboard header and (stretch) the progress-over-time chart.
Mapping 0-1 onto the 400-1600 scaled-score range is intentionally left out: that
needs real concordance data this project doesn't have.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime

from app.algorithm.decay import decayed_mastery
from app.algorithm.priority import TopicSnapshot
from app.enums import Section


def weighted_readiness(snapshots: Iterable[TopicSnapshot], now: datetime) -> float:
    """Frequency-weighted mean decayed mastery over the given topics, in [0, 1]."""
    items = list(snapshots)
    total_weight = sum(s.frequency_weight for s in items)
    if total_weight == 0:
        return 0.0
    earned = sum(
        s.frequency_weight * decayed_mastery(s.mastery_score, s.last_practiced, now) for s in items
    )
    return earned / total_weight


def readiness_by_section(snapshots: Iterable[TopicSnapshot], now: datetime) -> dict[Section, float]:
    """``weighted_readiness`` computed within each section."""
    grouped: dict[Section, list[TopicSnapshot]] = {}
    for snapshot in snapshots:
        grouped.setdefault(snapshot.section, []).append(snapshot)
    return {section: weighted_readiness(items, now) for section, items in grouped.items()}
