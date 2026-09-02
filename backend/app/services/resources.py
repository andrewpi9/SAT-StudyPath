"""Per-topic study resources.

The links are generic, real, free study destinations — a YouTube search scoped
to the skill and the relevant Khan Academy section. No proprietary or
paywalled content, and nothing that reproduces test material.
"""

from __future__ import annotations

from collections.abc import Iterable
from urllib.parse import quote_plus

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.enums import ResourceType, Section
from app.models.resource import Resource
from app.models.topic import Topic

_KHAN_SECTION_URL = {
    Section.MATH: "https://www.khanacademy.org/math",
    Section.READING_WRITING: "https://www.khanacademy.org/ela",
}
_KHAN_SECTION_LABEL = {
    Section.MATH: "Khan Academy — Math",
    Section.READING_WRITING: "Khan Academy — Reading & grammar",
}


def _resources_for_topic(topic: Topic) -> list[Resource]:
    query = quote_plus(f"digital SAT {topic.skill_name}")
    return [
        Resource(
            topic_id=topic.id,
            title=f"{topic.skill_name} — video walkthroughs",
            url=f"https://www.youtube.com/results?search_query={query}",
            type=ResourceType.VIDEO,
        ),
        Resource(
            topic_id=topic.id,
            title=_KHAN_SECTION_LABEL[topic.section],
            url=_KHAN_SECTION_URL[topic.section],
            type=ResourceType.ARTICLE,
        ),
    ]


def load_resources(db: Session) -> int:
    """Attach a couple of resources to every topic that has none. Idempotent."""
    have_resources = set(db.scalars(select(Resource.topic_id)))
    created = 0
    for topic in db.scalars(select(Topic)):
        if topic.id in have_resources:
            continue
        for resource in _resources_for_topic(topic):
            db.add(resource)
            created += 1
    db.flush()
    return created


def resources_for(db: Session, topic_ids: Iterable[int]) -> dict[int, list[Resource]]:
    ids = list(topic_ids)
    if not ids:
        return {}
    grouped: dict[int, list[Resource]] = {tid: [] for tid in ids}
    for resource in db.scalars(
        select(Resource).where(Resource.topic_id.in_(ids)).order_by(Resource.id)
    ):
        grouped.setdefault(resource.topic_id, []).append(resource)
    return grouped
