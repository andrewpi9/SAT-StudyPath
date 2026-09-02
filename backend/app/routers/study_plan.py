from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth import CurrentUser
from app.database import get_db
from app.schemas.resource import ResourceOut
from app.schemas.study_plan import StudyPlanItemOut, StudyPlanOut
from app.services.analytics import study_plan
from app.services.resources import resources_for
from app.utils.time import utcnow

router = APIRouter(prefix="/api", tags=["study-plan"])

# 35 topics in the taxonomy, so that's the natural upper bound on the plan.
_MAX_LIMIT = 35


@router.get("/study-plan", response_model=StudyPlanOut)
def get_study_plan(
    user: CurrentUser,
    limit: int = Query(5, ge=1, le=_MAX_LIMIT),
    db: Session = Depends(get_db),
) -> StudyPlanOut:
    """The ranked "study this next" list with per-topic reason strings and links."""
    now = utcnow()
    items = study_plan(db, user.id, now, limit)
    resource_map = resources_for(db, [item.topic_id for item in items])

    out_items: list[StudyPlanItemOut] = []
    for item in items:
        out = StudyPlanItemOut.model_validate(item)
        out.resources = [ResourceOut.model_validate(r) for r in resource_map.get(item.topic_id, [])]
        out_items.append(out)

    return StudyPlanOut(generated_at=now, limit=limit, items=out_items)
