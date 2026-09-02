from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.study_plan import StudyPlanItemOut, StudyPlanOut
from app.services.analytics import study_plan
from app.utils.time import utcnow

router = APIRouter(prefix="/api", tags=["study-plan"])

# 35 topics in the taxonomy, so that's the natural upper bound on the plan.
_MAX_LIMIT = 35


@router.get("/study-plan", response_model=StudyPlanOut)
def get_study_plan(
    limit: int = Query(5, ge=1, le=_MAX_LIMIT), db: Session = Depends(get_db)
) -> StudyPlanOut:
    """The ranked "study this next" list with per-topic reason strings."""
    now = utcnow()
    items = study_plan(db, now, limit)
    return StudyPlanOut(
        generated_at=now,
        limit=limit,
        items=[StudyPlanItemOut.model_validate(item) for item in items],
    )
