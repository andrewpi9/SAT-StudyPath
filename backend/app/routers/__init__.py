"""FastAPI routers, one module per resource."""

from app.routers import attempts, mastery, progress, resources, study_plan, topics

__all__ = ["attempts", "mastery", "progress", "resources", "study_plan", "topics"]
