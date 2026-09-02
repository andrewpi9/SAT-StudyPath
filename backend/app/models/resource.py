"""Resource: an external study link attached to a topic (stretch feature)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import ResourceType

if TYPE_CHECKING:
    from app.models.topic import Topic


class Resource(Base):
    __tablename__ = "resources"

    id: Mapped[int] = mapped_column(primary_key=True)
    topic_id: Mapped[int] = mapped_column(ForeignKey("topics.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    url: Mapped[str] = mapped_column(String(500))
    type: Mapped[ResourceType] = mapped_column(
        Enum(
            ResourceType,
            native_enum=False,
            length=16,
            values_callable=lambda e: [m.value for m in e],
        )
    )

    topic: Mapped["Topic"] = relationship(back_populates="resources")
