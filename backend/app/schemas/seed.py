from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class SeedRequest(BaseModel):
    """Options for POST /api/topics/seed (dev only)."""

    rng_seed: int = 42
    target_attempts: int | None = Field(default=None, ge=20, le=2000)
    reset: bool = True


class SeedResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    topics_created: int
    attempts_created: int
    reset: bool
