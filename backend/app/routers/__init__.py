"""FastAPI routers, one module per resource."""

from app.routers import attempts, auth, mastery, progress, resources, study_plan, topics

__all__ = ["auth", "attempts", "mastery", "progress", "resources", "study_plan", "topics"]
