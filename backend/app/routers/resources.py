from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.topic import Topic
from app.schemas.resource import ResourceOut
from app.services.resources import resources_for

router = APIRouter(prefix="/api/resources", tags=["resources"])


@router.get("/{topic_id}", response_model=list[ResourceOut])
def get_topic_resources(topic_id: int, db: Session = Depends(get_db)) -> list[ResourceOut]:
    """Study links (video / article) attached to one topic."""
    if db.get(Topic, topic_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Topic {topic_id} not found")
    found = resources_for(db, [topic_id]).get(topic_id, [])
    return [ResourceOut.model_validate(r) for r in found]
