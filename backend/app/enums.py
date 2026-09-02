"""Domain vocabulary shared by the models, the algorithm, and the API schemas.

These live outside ``app.models`` on purpose: the algorithm layer needs the
``Section`` enum for its reason strings but must not import the ORM package.

Stored in the database by *value* (``"Math"``, ``"easy"``) rather than by name,
via ``values_callable`` on the SQLAlchemy ``Enum`` type, so raw rows stay
human-readable.
"""

from __future__ import annotations

from enum import StrEnum


class Section(StrEnum):
    MATH = "Math"
    READING_WRITING = "ReadingWriting"

    @property
    def label(self) -> str:
        """Human-facing name (the stored value squashes 'Reading & Writing')."""
        return "Reading & Writing" if self is Section.READING_WRITING else "Math"


class Difficulty(StrEnum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class ResourceType(StrEnum):
    VIDEO = "video"
    ARTICLE = "article"
