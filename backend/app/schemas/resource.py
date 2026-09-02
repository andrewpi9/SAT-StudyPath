from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.enums import ResourceType


class ResourceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    topic_id: int
    title: str
    url: str
    type: ResourceType
