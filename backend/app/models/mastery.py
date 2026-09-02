"""TopicMastery: one user's running estimate of how well a topic is known.

``mastery_score`` and ``confidence`` are updated incrementally on every attempt
(exponentially weighted moving average -- see ``app.algorithm.mastery``).
Forgetting-curve decay is applied at *read* time, not stored here, so the raw
number always reflects "how well did you do when you last practiced".

Primary key is ``(user_id, topic_id)`` -- one row per user per topic, created
lazily on that user's first attempt.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.algorithm.mastery import COLD_START_MASTERY
from app.models.base import Base


class TopicMastery(Base):
    __tablename__ = "topic_mastery"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    topic_id: Mapped[int] = mapped_column(
        ForeignKey("topics.id", ondelete="CASCADE"), primary_key=True
    )
    mastery_score: Mapped[float] = mapped_column(Float, default=COLD_START_MASTERY)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    attempts_count: Mapped[int] = mapped_column(Integer, default=0)
    last_practiced: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return (
            f"<TopicMastery user={self.user_id} topic={self.topic_id} "
            f"score={self.mastery_score:.2f} n={self.attempts_count}>"
        )
