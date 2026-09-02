"""Topic: one testable SAT skill within a domain. Global reference data."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Enum, Float, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.enums import Section
from app.models.base import Base

if TYPE_CHECKING:
    from app.models.resource import Resource


class Topic(Base):
    __tablename__ = "topics"

    id: Mapped[int] = mapped_column(primary_key=True)
    section: Mapped[Section] = mapped_column(
        Enum(Section, native_enum=False, length=32, values_callable=lambda e: [m.value for m in e])
    )
    domain: Mapped[str] = mapped_column(String(64), index=True)
    skill_name: Mapped[str] = mapped_column(String(128), unique=True)

    # Relative frequency of this skill *within its section*; the weights in a
    # section sum to ~1.0. Seeded from approximate, tutor-informed digital-SAT
    # test-spec weightings (see app/data/taxonomy.py) -- not scraped from any
    # proprietary source.
    frequency_weight: Mapped[float] = mapped_column(Float)

    resources: Mapped[list["Resource"]] = relationship(
        back_populates="topic", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"<Topic {self.id} {self.section}/{self.skill_name!r}>"
