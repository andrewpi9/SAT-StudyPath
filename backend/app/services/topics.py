"""Loading the topic taxonomy into the database."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.data.taxonomy import TAXONOMY
from app.models.topic import Topic


def load_taxonomy(db: Session) -> list[Topic]:
    """Insert any taxonomy skills not already present. Idempotent.

    Topics are global reference data. Per-user ``TopicMastery`` rows are created
    lazily on that user's first attempt (a never-attempted topic still surfaces
    in the study plan via the exploration bonus, at its cold-start score).
    """
    existing = {name for name in db.scalars(select(Topic.skill_name))}
    created: list[Topic] = []

    for spec in TAXONOMY:
        if spec.skill_name in existing:
            continue
        db.add(
            topic := Topic(
                section=spec.section,
                domain=spec.domain,
                skill_name=spec.skill_name,
                frequency_weight=spec.frequency_weight,
            )
        )
        created.append(topic)

    db.flush()
    return created
