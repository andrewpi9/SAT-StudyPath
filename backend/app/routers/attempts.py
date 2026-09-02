from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.algorithm.priority import evaluate_topic
from app.auth import CurrentUser
from app.database import get_db
from app.models.topic import Topic
from app.schemas.attempt import (
    AttemptCreate,
    AttemptOut,
    AttemptResultOut,
    BulkImportError,
    BulkImportResult,
)
from app.schemas.mastery import TopicMasteryOut
from app.services.analytics import topic_snapshot
from app.services.attempts import record_attempt
from app.services.bulk_import import TEMPLATE_CSV, import_attempts_csv
from app.utils.time import utcnow

router = APIRouter(prefix="/api/attempts", tags=["attempts"])

_MAX_UPLOAD_BYTES = 1_000_000


@router.post("", response_model=AttemptResultOut, status_code=status.HTTP_201_CREATED)
def log_attempt(
    payload: AttemptCreate, user: CurrentUser, db: Session = Depends(get_db)
) -> AttemptResultOut:
    """Record one practice outcome and return the topic's updated mastery."""
    topic = db.get(Topic, payload.topic_id)
    if topic is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Topic {payload.topic_id} not found")

    attempt = record_attempt(
        db,
        user_id=user.id,
        topic_id=payload.topic_id,
        correct=payload.correct,
        time_taken_seconds=payload.time_taken_seconds,
        difficulty=payload.difficulty,
    )
    db.commit()

    scored = evaluate_topic(topic_snapshot(db, user.id, topic), utcnow())
    return AttemptResultOut(
        attempt=AttemptOut.model_validate(attempt),
        mastery=TopicMasteryOut.model_validate(scored),
    )


@router.get("/template.csv", response_class=Response)
def bulk_template() -> Response:
    """A ready-to-fill CSV showing the accepted columns."""
    return Response(
        TEMPLATE_CSV,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="attempts-template.csv"'},
    )


@router.post("/bulk", response_model=BulkImportResult, status_code=status.HTTP_201_CREATED)
async def bulk_import(
    user: CurrentUser, file: UploadFile, db: Session = Depends(get_db)
) -> BulkImportResult:
    """Import many attempts from a CSV file (see GET /api/attempts/template.csv)."""
    if file.filename and not file.filename.lower().endswith(".csv"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Expected a .csv file")

    raw = await file.read()
    if len(raw) > _MAX_UPLOAD_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "File too large (1 MB max)")
    try:
        content = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "File must be UTF-8 encoded text") from exc

    result = import_attempts_csv(db, user.id, content)
    return BulkImportResult(
        imported=result.imported,
        failed=result.failed,
        errors=[BulkImportError(row=e.row, message=e.message) for e in result.errors],
    )
