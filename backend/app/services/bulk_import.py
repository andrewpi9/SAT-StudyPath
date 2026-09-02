"""CSV bulk import of practice attempts.

Accepts a forgiving CSV: header names and enum values are matched
case-insensitively, ``time`` and ``difficulty`` are optional, and an optional
``days_ago`` column backdates a row so an imported practice test from last week
decays correctly.

    topic,correct,time_taken_seconds,difficulty,days_ago
    Linear functions,true,55,medium,3
    Percentages,0,,hard,3

Rows are validated up front; only fully-valid rows reach ``record_attempt``, so a
bad row never leaves partial state behind.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.enums import Difficulty
from app.models.topic import Topic
from app.services.attempts import record_attempt
from app.utils.time import utcnow

_TRUE = {"true", "t", "1", "yes", "y", "correct", "c", "right"}
_FALSE = {"false", "f", "0", "no", "n", "incorrect", "i", "wrong"}

# Header aliases -> canonical field name.
_ALIASES = {
    "topic": "topic",
    "skill": "topic",
    "skill_name": "topic",
    "topic_id": "topic_id",
    "correct": "correct",
    "outcome": "correct",
    "result": "correct",
    "time_taken_seconds": "time",
    "time": "time",
    "seconds": "time",
    "difficulty": "difficulty",
    "days_ago": "days_ago",
}

MAX_ROWS = 5000
TEMPLATE_CSV = (
    "topic,correct,time_taken_seconds,difficulty,days_ago\n"
    "Linear functions,true,55,medium,2\n"
    "Percentages,false,90,hard,2\n"
    "Words in context,correct,40,easy,0\n"
)


@dataclass
class RowError:
    row: int
    message: str


@dataclass
class BulkResult:
    imported: int = 0
    errors: list[RowError] = field(default_factory=list)

    @property
    def failed(self) -> int:
        return len(self.errors)


def _normalise(raw: dict[str, str | None]) -> dict[str, str]:
    out: dict[str, str] = {}
    for key, value in raw.items():
        canon = _ALIASES.get((key or "").strip().lower())
        if canon:
            out[canon] = (value or "").strip()
    return out


def import_attempts_csv(db: Session, user_id: int, content: str) -> BulkResult:
    reader = csv.DictReader(io.StringIO(content))
    if not reader.fieldnames:
        return BulkResult(errors=[RowError(0, "The file appears to be empty.")])

    all_topics = list(db.scalars(select(Topic)))
    by_name = {t.skill_name.lower(): t for t in all_topics}
    by_id = {t.id: t for t in all_topics}
    result = BulkResult()
    now = utcnow()

    for line_no, raw in enumerate(reader, start=2):  # line 1 is the header
        if line_no - 1 > MAX_ROWS:
            result.errors.append(RowError(line_no, f"Stopped at the {MAX_ROWS}-row limit."))
            break

        row = _normalise(raw)
        if not any(row.values()):
            continue  # skip blank lines

        parsed = _parse_row(row, by_name, by_id)
        if isinstance(parsed, str):
            result.errors.append(RowError(line_no, parsed))
            continue

        topic_id, correct, seconds, difficulty, days_ago = parsed
        record_attempt(
            db,
            user_id=user_id,
            topic_id=topic_id,
            correct=correct,
            time_taken_seconds=seconds,
            difficulty=difficulty,
            timestamp=now - timedelta(days=days_ago),
        )
        result.imported += 1

    if result.imported:
        db.commit()
    else:
        db.rollback()
    return result


def _parse_row(
    row: dict[str, str], by_name: dict[str, Topic], by_id: dict[int, Topic]
) -> tuple[int, bool, int, Difficulty, float] | str:
    """Return ``(topic_id, correct, seconds, difficulty, days_ago)`` or an error string."""
    topic_ref = row.get("topic") or row.get("topic_id")
    if not topic_ref:
        return "Missing 'topic'."
    topic = by_name.get(topic_ref.lower())
    if topic is None and topic_ref.isdigit():
        topic = by_id.get(int(topic_ref))
    if topic is None:
        return f"Unknown topic {topic_ref!r}."

    raw_correct = row.get("correct", "").lower()
    if raw_correct in _TRUE:
        correct = True
    elif raw_correct in _FALSE:
        correct = False
    else:
        return f"'correct' must be true/false, got {row.get('correct', '')!r}."

    seconds_raw = row.get("time") or "60"
    try:
        seconds = int(float(seconds_raw))
    except ValueError:
        return f"'time_taken_seconds' must be a number, got {seconds_raw!r}."
    if not 1 <= seconds <= 3600:
        return "'time_taken_seconds' must be between 1 and 3600."

    difficulty_raw = (row.get("difficulty") or "medium").lower()
    try:
        difficulty = Difficulty(difficulty_raw)
    except ValueError:
        return f"'difficulty' must be easy/medium/hard, got {difficulty_raw!r}."

    days_ago_raw = row.get("days_ago") or "0"
    try:
        days_ago = max(0.0, float(days_ago_raw))
    except ValueError:
        return f"'days_ago' must be a number, got {days_ago_raw!r}."

    return topic.id, correct, seconds, difficulty, days_ago
