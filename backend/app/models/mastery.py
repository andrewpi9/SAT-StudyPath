"""TopicMastery: the running estimate of how well a topic is known.

``mastery_score`` and ``confidence`` are updated incrementally on every attempt
(exponentially weighted moving average -- see ``app.algorithm.mastery``).
Forgetting-curve decay is applied at *read* time, not stored here, so the raw
number always reflects "how well did you do when you last practiced".
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.algorithm.mastery import COLD_START_MASTERY
from app.models.base import Base

if TYPE_CHECKING:
    from app.models.topic import Topic


class TopicMastery(Base):
    __tablename__ = "topic_mastery"

    topic_id: Mapped[int] = mapped_column(
        ForeignKey("topics.id", ondelete="CASCADE"), primary_key=True
    )
    mastery_score: Mapped[float] = mapped_column(Float, default=COLD_START_MASTERY)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    attempts_count: Mapped[int] = mapped_column(Integer, default=0)
    last_practiced: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    topic: Mapped["Topic"] = relationship(back_populates="mastery")

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return (
            f"<TopicMastery topic={self.topic_id} score={self.mastery_score:.2f} "
            f"n={self.attempts_count}>"
        )
