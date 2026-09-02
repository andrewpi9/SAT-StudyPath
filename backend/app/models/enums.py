"""Enumerations shared across models and API schemas.

Stored in the database by *value* (``"Math"``, ``"easy"``) rather than by name,
via ``values_callable`` on the SQLAlchemy ``Enum`` type, so the raw rows stay
human-readable.
"""

from __future__ import annotations

from enum import StrEnum


class Section(StrEnum):
    MATH = "Math"
    READING_WRITING = "ReadingWriting"


class Difficulty(StrEnum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class ResourceType(StrEnum):
    VIDEO = "video"
    ARTICLE = "article"
