"""Read-side services: turn ORM state into algorithm inputs and back.

Every endpoint that reports on mastery (the dashboard, the study plan, the
per-attempt response) funnels through ``topic_snapshots`` so the projection from
ORM -> ``TopicSnapshot`` lives in one place.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.algorithm.mastery import COLD_START_MASTERY
from app.algorithm.priority import Recommendation, TopicSnapshot, evaluate_topic, rank_topics
from app.algorithm.readiness import readiness_by_section, weighted_readiness
from app.enums import Section
from app.models.topic import Topic


@dataclass(frozen=True)
class ReadinessBreakdown:
    overall: float
    by_section: dict[Section, float]


def topic_to_snapshot(topic: Topic) -> TopicSnapshot:
    """One ORM ``Topic`` (with its mastery row) -> the algorithm's input type."""
    mastery = topic.mastery
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


def topic_snapshots(db: Session) -> list[TopicSnapshot]:
    topics = db.scalars(select(Topic).options(selectinload(Topic.mastery)).order_by(Topic.id)).all()
    return [topic_to_snapshot(t) for t in topics]


def mastery_overview(db: Session, now: datetime) -> list[Recommendation]:
    """Every topic scored, ordered for the dashboard (section, domain, then weight)."""
    scored = [evaluate_topic(s, now) for s in topic_snapshots(db)]
    scored.sort(key=lambda r: (r.section.value, r.domain, -r.frequency_weight, r.skill_name))
    return scored


def study_plan(db: Session, now: datetime, limit: int) -> list[Recommendation]:
    return rank_topics(topic_snapshots(db), now=now, limit=limit)


def readiness(db: Session, now: datetime) -> ReadinessBreakdown:
    snapshots = topic_snapshots(db)
    return ReadinessBreakdown(
        overall=weighted_readiness(snapshots, now),
        by_section=readiness_by_section(snapshots, now),
    )
