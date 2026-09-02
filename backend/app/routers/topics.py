from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.topic import Topic
from app.schemas.seed import SeedRequest, SeedResultOut
from app.schemas.topic import TopicOut
from app.services.seeding import seed_database

router = APIRouter(prefix="/api/topics", tags=["topics"])


@router.get("", response_model=list[TopicOut])
def list_topics(db: Session = Depends(get_db)) -> list[Topic]:
    """The full skill taxonomy, ordered section -> domain -> weight."""
    return list(
        db.scalars(
            select(Topic).order_by(
                Topic.section, Topic.domain, Topic.frequency_weight.desc(), Topic.skill_name
            )
        )
    )


@router.post("/seed", response_model=SeedResultOut, status_code=status.HTTP_201_CREATED)
def seed(payload: SeedRequest | None = None, db: Session = Depends(get_db)) -> SeedResultOut:
    """Dev only: (re)load the taxonomy and a synthetic practice history."""
    if not settings.enable_dev_endpoints:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Seeding is disabled (ENABLE_DEV_ENDPOINTS=false)"
        )
    payload = payload or SeedRequest()
    result = seed_database(
        db,
        rng_seed=payload.rng_seed,
        target_attempts=payload.target_attempts,
        reset=payload.reset,
    )
    return SeedResultOut.model_validate(result)
