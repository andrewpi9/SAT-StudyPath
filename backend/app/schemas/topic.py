from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.enums import Section


class TopicOut(BaseModel):
    """One skill in the taxonomy."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    section: Section
    domain: str
    skill_name: str
    frequency_weight: float
