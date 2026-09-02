from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class ReadinessPointOut(BaseModel):
    day: date
    overall_readiness: float
    math_readiness: float
    reading_writing_readiness: float


class ProgressOut(BaseModel):
    range_days: int
    points: list[ReadinessPointOut]
