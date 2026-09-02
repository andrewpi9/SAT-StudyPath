"""Attempt: one user's single practice question outcome for a topic.

Only topic tag + metadata is stored -- never real question text or passages.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.enums import Difficulty
from app.models.base import Base
from app.utils.time import utcnow


class Attempt(Base):
    __tablename__ = "attempts"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    topic_id: Mapped[int] = mapped_column(ForeignKey("topics.id", ondelete="CASCADE"), index=True)
    correct: Mapped[bool] = mapped_column(Boolean)
    time_taken_seconds: Mapped[int] = mapped_column(Integer)
    difficulty: Mapped[Difficulty] = mapped_column(
        Enum(
            Difficulty, native_enum=False, length=16, values_callable=lambda e: [m.value for m in e]
        )
    )
    # Naive UTC. Backdated by the seed script to simulate a multi-week history.
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        mark = "correct" if self.correct else "wrong"
        return f"<Attempt {self.id} user={self.user_id} topic={self.topic_id} {mark}>"
