"""Forgetting-curve decay, applied at read time.

Skills fade when they aren't practised. Ebbinghaus's forgetting curve models
retention as exponential decay over elapsed time, and that's exactly what we
apply here: the longer a topic goes untouched, the more its *effective* mastery
slides below the number the student earned when they last practised.

This is deliberately **not** stored. ``TopicMastery.mastery_score`` always means
"how well did you do when you last worked on this"; decay is a lens applied when
we read that number to rank topics or draw the dashboard. Practising the topic
again writes a fresh score and resets the clock -- so a quick review session
restores most of the lost ground, which is the spaced-repetition behaviour we
want the study plan to encourage.

Pure functions, no database, no ``datetime.now()`` inside -- the caller passes
``now`` so tests are deterministic.
"""

from __future__ import annotations

import math
from datetime import datetime

# Per-day exponential decay constant. exp(-0.02 * 7) ~= 0.869, i.e. a topic left
# untouched for a week loses ~13% of its mastery; ~25% over 15 days; ~45% over a
# month. Tuned to be noticeable within a typical study cycle without nuking a
# skill the student genuinely learned.
DECAY_RATE: float = 0.02


def days_since_practice(last_practiced: datetime | None, now: datetime) -> int | None:
    """Whole days from ``last_practiced`` to ``now``; ``None`` if never practised.

    Clamped at 0 so clock skew (a timestamp slightly in the future) can't produce
    negative decay, which would *inflate* mastery.
    """
    if last_practiced is None:
        return None
    return max(0, (now - last_practiced).days)


def decayed_mastery(
    mastery_score: float,
    last_practiced: datetime | None,
    now: datetime,
    decay_rate: float = DECAY_RATE,
) -> float:
    """Effective mastery right now, after forgetting.

    ``decayed = mastery_score * exp(-decay_rate * days_since_practice)``

    A never-practised topic has nothing to forget, so its cold-start score is
    returned unchanged. The result is always in ``[0, mastery_score]``.
    """
    elapsed = days_since_practice(last_practiced, now)
    if not elapsed:  # None (never practised) or 0 (practised today)
        return mastery_score
    return mastery_score * math.exp(-decay_rate * elapsed)
