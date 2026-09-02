from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.enums import Section


class TopicMasteryOut(BaseModel):
    """A topic's current mastery picture: the stored estimate plus the
    read-time forgetting-curve view of it."""

    model_config = ConfigDict(from_attributes=True)

    topic_id: int
    skill_name: str
    section: Section
    domain: str
    frequency_weight: float

    mastery_score: float  # stored EWMA estimate (as of last practice)
    decayed_mastery: float  # after forgetting-curve decay, right now
    confidence: float  # 0-1, grows with attempt volume
    attempts_count: int
    last_practiced: datetime | None
    days_since_practice: int | None


class MasteryOverviewOut(BaseModel):
    """Everything the dashboard needs in one call."""

    generated_at: datetime
    overall_readiness: float
    section_readiness: dict[Section, float]
    topics: list[TopicMasteryOut]
