from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.enums import Difficulty
from app.schemas.mastery import TopicMasteryOut


class AttemptCreate(BaseModel):
    """Payload for POST /api/attempts -- one practice question outcome."""

    topic_id: int
    correct: bool
    time_taken_seconds: int = Field(gt=0, le=3600)
    difficulty: Difficulty


class AttemptOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    topic_id: int
    correct: bool
    time_taken_seconds: int
    difficulty: Difficulty
    timestamp: datetime


class AttemptResultOut(BaseModel):
    """The logged attempt plus the topic's freshly updated mastery, so the UI
    can reflect the change without a second request."""

    attempt: AttemptOut
    mastery: TopicMasteryOut
