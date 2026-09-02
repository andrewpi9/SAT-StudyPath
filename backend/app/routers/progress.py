from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.enums import Section
from app.schemas.progress import ProgressOut, ReadinessPointOut
from app.services.progress import MAX_RANGE_DAYS, get_readiness_series

router = APIRouter(prefix="/api", tags=["progress"])


@router.get("/progress", response_model=ProgressOut)
def get_progress(
    days: int = Query(30, ge=1, le=MAX_RANGE_DAYS), db: Session = Depends(get_db)
) -> ProgressOut:
    """Frequency-weighted readiness for each of the last ``days`` days, replayed
    from the attempt history."""
    series = get_readiness_series(db, days)
    return ProgressOut(
        range_days=days,
        points=[
            ReadinessPointOut(
                day=point.day,
                overall_readiness=point.overall,
                math_readiness=point.by_section.get(Section.MATH, 0.0),
                reading_writing_readiness=point.by_section.get(Section.READING_WRITING, 0.0),
            )
            for point in series
        ],
    )
