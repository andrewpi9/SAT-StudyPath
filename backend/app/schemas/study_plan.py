from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.enums import Section


class StudyPlanItemOut(BaseModel):
    """One ranked recommendation, with the full score breakdown so the reasoning
    is inspectable (and the reason string, for humans)."""

    model_config = ConfigDict(from_attributes=True)

    topic_id: int
    skill_name: str
    section: Section
    domain: str
    frequency_weight: float

    mastery_score: float
    decayed_mastery: float
    confidence: float
    attempts_count: int
    last_practiced: datetime | None
    days_since_practice: int | None

    urgency: float
    exploration_bonus: float
    priority_score: float
    reason: str


class StudyPlanOut(BaseModel):
    generated_at: datetime
    limit: int
    items: list[StudyPlanItemOut]
