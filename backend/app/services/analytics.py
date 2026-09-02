"""Read-side services: turn one user's ORM state into algorithm inputs and back.

Every endpoint that reports on mastery (the dashboard, the study plan, the
per-attempt response) funnels through ``topic_snapshots`` so the projection from
ORM -> ``TopicSnapshot`` lives in one place.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.algorithm.mastery import COLD_START_MASTERY
from app.algorithm.priority import Recommendation, TopicSnapshot, evaluate_topic, rank_topics
from app.algorithm.readiness import readiness_by_section, weighted_readiness
from app.enums import Section
from app.models.mastery import TopicMastery
from app.models.topic import Topic


@dataclass(frozen=True)
class ReadinessBreakdown:
    overall: float
    by_section: dict[Section, float]


def _snapshot(topic: Topic, mastery: TopicMastery | None) -> TopicSnapshot:
    return TopicSnapshot(
        topic_id=topic.id,
        section=topic.section,
        domain=topic.domain,
        skill_name=topic.skill_name,
        frequency_weight=topic.frequency_weight,
        mastery_score=mastery.mastery_score if mastery else COLD_START_MASTERY,
        attempts_count=mastery.attempts_count if mastery else 0,
        last_practiced=mastery.last_practiced if mastery else None,
    )


def topic_snapshots(db: Session, user_id: int) -> list[TopicSnapshot]:
    """One snapshot per topic for ``user_id`` -- cold-start where they've never
    practised it."""
    topics = db.scalars(select(Topic).order_by(Topic.id)).all()
    mastery_by_topic = {
        m.topic_id: m
        for m in db.scalars(select(TopicMastery).where(TopicMastery.user_id == user_id))
    }
    return [_snapshot(topic, mastery_by_topic.get(topic.id)) for topic in topics]


def topic_snapshot(db: Session, user_id: int, topic: Topic) -> TopicSnapshot:
    mastery = db.get(TopicMastery, (user_id, topic.id))
    return _snapshot(topic, mastery)


def mastery_overview(db: Session, user_id: int, now: datetime) -> list[Recommendation]:
    """Every topic scored, ordered for the dashboard (section, domain, weight)."""
    scored = [evaluate_topic(s, now) for s in topic_snapshots(db, user_id)]
    scored.sort(key=lambda r: (r.section.value, r.domain, -r.frequency_weight, r.skill_name))
    return scored


def study_plan(db: Session, user_id: int, now: datetime, limit: int) -> list[Recommendation]:
    return rank_topics(topic_snapshots(db, user_id), now=now, limit=limit)


def readiness(db: Session, user_id: int, now: datetime) -> ReadinessBreakdown:
    snapshots = topic_snapshots(db, user_id)
    return ReadinessBreakdown(
        overall=weighted_readiness(snapshots, now),
        by_section=readiness_by_section(snapshots, now),
    )
