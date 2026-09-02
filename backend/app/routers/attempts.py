from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.algorithm.priority import evaluate_topic
from app.database import get_db
from app.models.topic import Topic
from app.schemas.attempt import AttemptCreate, AttemptOut, AttemptResultOut
from app.schemas.mastery import TopicMasteryOut
from app.services.analytics import topic_to_snapshot
from app.services.attempts import record_attempt
from app.utils.time import utcnow

router = APIRouter(prefix="/api/attempts", tags=["attempts"])


@router.post("", response_model=AttemptResultOut, status_code=status.HTTP_201_CREATED)
def log_attempt(payload: AttemptCreate, db: Session = Depends(get_db)) -> AttemptResultOut:
    """Record one practice outcome and return the topic's updated mastery."""
    topic = db.get(Topic, payload.topic_id)
    if topic is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Topic {payload.topic_id} not found")

    attempt = record_attempt(
        db,
        topic_id=payload.topic_id,
        correct=payload.correct,
        time_taken_seconds=payload.time_taken_seconds,
        difficulty=payload.difficulty,
    )
    db.commit()
    db.refresh(topic)

    scored = evaluate_topic(topic_to_snapshot(topic), utcnow())
    return AttemptResultOut(
        attempt=AttemptOut.model_validate(attempt),
        mastery=TopicMasteryOut.model_validate(scored),
    )
