"""FastAPI routers, one module per resource."""

from app.routers import attempts, mastery, study_plan, topics

__all__ = ["attempts", "mastery", "study_plan", "topics"]
