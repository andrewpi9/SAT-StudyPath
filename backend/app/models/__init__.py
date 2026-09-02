"""ORM models.

Importing this package pulls in every model so that
``Base.metadata.create_all()`` sees the full schema and relationship strings
resolve.
"""

from app.models.attempt import Attempt
from app.models.base import Base
from app.models.enums import Difficulty, ResourceType, Section
from app.models.mastery import TopicMastery
from app.models.resource import Resource
from app.models.topic import Topic

__all__ = [
    "Attempt",
    "Base",
    "Difficulty",
    "ResourceType",
    "Section",
    "Topic",
    "TopicMastery",
    "Resource",
]
