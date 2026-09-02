from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.mastery import MasteryOverviewOut, TopicMasteryOut
from app.services.analytics import mastery_overview, readiness
from app.utils.time import utcnow

router = APIRouter(prefix="/api", tags=["mastery"])


@router.get("/mastery", response_model=MasteryOverviewOut)
def get_mastery(db: Session = Depends(get_db)) -> MasteryOverviewOut:
    """Every topic's mastery/decay/confidence, plus the readiness roll-up."""
    now = utcnow()
    scored = mastery_overview(db, now)
    breakdown = readiness(db, now)
    return MasteryOverviewOut(
        generated_at=now,
        overall_readiness=breakdown.overall,
        section_readiness=breakdown.by_section,
        topics=[TopicMasteryOut.model_validate(rec) for rec in scored],
    )
