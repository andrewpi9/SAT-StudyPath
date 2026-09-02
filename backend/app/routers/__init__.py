"""FastAPI routers, one module per resource."""

from app.routers import attempts, mastery, progress, study_plan, topics

__all__ = ["attempts", "mastery", "progress", "study_plan", "topics"]
