"""Hand-computed tests for the recommendation engine.

This is the file to walk an interviewer through. Every expected number is worked
out by hand in a comment next to the assertion -- the tests exist to pin down the
*behaviour* of the algorithm, not just to check it doesn't raise.

Layout mirrors the pipeline:
    1. update_mastery        - EWMA on each attempt              (spec 7.1)
    2. confidence_from_attempts                                  (spec 7.1)
    3. decayed_mastery       - forgetting curve at read time     (spec 7.2)
    4. exploration_bonus / priority_score                        (spec 7.3)
    5. rank_topics           - the four edge cases               (spec 7.4)
    6. build_reason          - the human-readable "why"
    7. weighted_readiness    - the dashboard roll-up
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta

import pytest

from app.algorithm.decay import DECAY_RATE, days_since_practice, decayed_mastery
from app.algorithm.mastery import (
    COLD_START_MASTERY,
    LEARNING_RATE,
    confidence_from_attempts,
    update_mastery,
)
from app.algorithm.priority import (
    Recommendation,
    TopicSnapshot,
    build_reason,
    exploration_bonus,
    priority_score,
    rank_topics,
    study_plan,
)
from app.algorithm.readiness import readiness_by_section, weighted_readiness
from app.enums import Section

NOW = datetime(2026, 3, 1, 12, 0, 0)


def _snapshot(
    *,
    topic_id: int = 1,
    section: Section = Section.MATH,
    domain: str = "Algebra",
    skill_name: str = "Linear functions",
    frequency_weight: float = 0.08,
    mastery_score: float = COLD_START_MASTERY,
    attempts_count: int = 0,
    days_ago: int | None = None,
) -> TopicSnapshot:
    last_practiced = None if days_ago is None else NOW - timedelta(days=days_ago)
    return TopicSnapshot(
        topic_id=topic_id,
        section=section,
        domain=domain,
        skill_name=skill_name,
        frequency_weight=frequency_weight,
        mastery_score=mastery_score,
        attempts_count=attempts_count,
        last_practiced=last_practiced,
    )


# ---------------------------------------------------------------------------
# 1. update_mastery  --  new = old + lr * (outcome - old),  lr = 0.3
# ---------------------------------------------------------------------------


class TestUpdateMastery:
    def test_default_learning_rate_is_documented_value(self) -> None:
        assert LEARNING_RATE == 0.3
        assert COLD_START_MASTERY == 0.4

    def test_correct_attempt_from_cold_start(self) -> None:
        # 0.4 + 0.3 * (1.0 - 0.4) = 0.4 + 0.18 = 0.58
        assert update_mastery(0.4, correct=True) == pytest.approx(0.58)

    def test_wrong_attempt_from_cold_start(self) -> None:
        # 0.4 + 0.3 * (0.0 - 0.4) = 0.4 - 0.12 = 0.28
        assert update_mastery(0.4, correct=False) == pytest.approx(0.28)

    def test_three_correct_in_a_row_from_cold_start(self) -> None:
        # 0.4 -> 0.58 -> 0.706 -> 0.7942
        m = COLD_START_MASTERY
        for _ in range(3):
            m = update_mastery(m, correct=True)
        assert m == pytest.approx(0.7942)

    def test_three_wrong_in_a_row_from_cold_start(self) -> None:
        # 0.4 -> 0.28 -> 0.196 -> 0.1372
        m = COLD_START_MASTERY
        for _ in range(3):
            m = update_mastery(m, correct=False)
        assert m == pytest.approx(0.1372)

    def test_recent_attempts_dominate_old_ones(self) -> None:
        # Same 10 outcomes, opposite order. EWMA should weight the *recent* ones,
        # so "ended on a good run" scores higher than "ended on a bad run".
        outcomes = [True, True, True, True, True, False, False, False, False, False]

        ending_bad = COLD_START_MASTERY
        for ok in outcomes:
            ending_bad = update_mastery(ending_bad, correct=ok)

        ending_good = COLD_START_MASTERY
        for ok in reversed(outcomes):
            ending_good = update_mastery(ending_good, correct=ok)

        assert ending_good > ending_bad + 0.3  # a large, decisive gap

    def test_stays_within_bounds_at_the_extremes(self) -> None:
        assert update_mastery(1.0, correct=True) == pytest.approx(1.0)
        assert update_mastery(0.0, correct=False) == pytest.approx(0.0)
        # A wrong answer on a maxed-out topic: 1.0 + 0.3 * (0 - 1.0) = 0.7
        assert update_mastery(1.0, correct=False) == pytest.approx(0.7)

    def test_learning_rate_is_overridable(self) -> None:
        # 0.5 + 0.5 * (1.0 - 0.5) = 0.75
        assert update_mastery(0.5, correct=True, learning_rate=0.5) == pytest.approx(0.75)


# ---------------------------------------------------------------------------
# 2. confidence_from_attempts  --  min(1.0, n / 5)
# ---------------------------------------------------------------------------


class TestConfidence:
    @pytest.mark.parametrize(
        ("attempts", "expected"),
        [(0, 0.0), (1, 0.2), (2, 0.4), (3, 0.6), (4, 0.8), (5, 1.0), (9, 1.0)],
    )
    def test_grows_then_saturates(self, attempts: int, expected: float) -> None:
        assert confidence_from_attempts(attempts) == pytest.approx(expected)

    def test_negative_is_treated_as_zero(self) -> None:
        assert confidence_from_attempts(-3) == 0.0


# ---------------------------------------------------------------------------
# 3. decayed_mastery  --  score * exp(-0.02 * days_since_practice)
# ---------------------------------------------------------------------------


class TestDecay:
    def test_decay_rate_is_documented_value(self) -> None:
        assert DECAY_RATE == 0.02
        # The headline claim: ~13% lost over a week untouched.
        assert 1 - math.exp(-DECAY_RATE * 7) == pytest.approx(0.13, abs=0.005)

    def test_no_decay_on_the_day_of_practice(self) -> None:
        assert decayed_mastery(0.8, NOW, NOW) == 0.8

    def test_never_practiced_topic_keeps_its_cold_start_score(self) -> None:
        assert decayed_mastery(COLD_START_MASTERY, None, NOW) == COLD_START_MASTERY
        assert days_since_practice(None, NOW) is None

    def test_one_week_untouched(self) -> None:
        # 0.8 * exp(-0.14) = 0.8 * 0.869358 = 0.695487
        assert decayed_mastery(0.8, NOW - timedelta(days=7), NOW) == pytest.approx(
            0.695487, abs=1e-6
        )

    def test_one_month_untouched_roughly_halves_a_strong_score(self) -> None:
        # 0.95 * exp(-0.60) = 0.95 * 0.548812 = 0.521371
        assert decayed_mastery(0.95, NOW - timedelta(days=30), NOW) == pytest.approx(
            0.521371, abs=1e-6
        )

    def test_future_timestamp_does_not_inflate_mastery(self) -> None:
        # Clock skew -> clamp elapsed days at 0, so decay never runs backwards.
        assert days_since_practice(NOW + timedelta(days=3), NOW) == 0
        assert decayed_mastery(0.8, NOW + timedelta(days=3), NOW) == 0.8

    def test_partial_days_floor_like_the_spec(self) -> None:
        # spec uses (now - last_practiced).days -- whole days only
        assert days_since_practice(NOW - timedelta(days=6, hours=23), NOW) == 6


# ---------------------------------------------------------------------------
# 4. exploration_bonus = 0.15 / (1 + n)   and   priority_score
# ---------------------------------------------------------------------------


class TestExplorationBonus:
    @pytest.mark.parametrize(
        ("attempts", "expected"),
        [(0, 0.15), (1, 0.075), (2, 0.05), (4, 0.03), (9, 0.015), (14, 0.01)],
    )
    def test_shrinks_as_attempts_accumulate(self, attempts: int, expected: float) -> None:
        assert exploration_bonus(attempts) == pytest.approx(expected)


class TestPriorityScore:
    def test_worked_example(self) -> None:
        # fw 0.08, decayed mastery 0.72 (urgency 0.28), 6 attempts
        # 0.08 * 0.28 + 0.15 / 7 = 0.0224 + 0.021429 = 0.043829
        assert priority_score(0.08, 0.72, 6) == pytest.approx(0.043829, abs=1e-6)

    def test_never_attempted_is_dominated_by_the_exploration_term(self) -> None:
        # fw 0.05, cold mastery 0.4 (urgency 0.6), 0 attempts
        # 0.05 * 0.6 + 0.15 = 0.03 + 0.15 = 0.18
        assert priority_score(0.05, 0.4, 0) == pytest.approx(0.18)

    def test_fully_mastered_and_fresh_scores_almost_nothing(self) -> None:
        # urgency 0, so only the (tiny) exploration term remains: 0.15 / 13
        assert priority_score(0.08, 1.0, 12) == pytest.approx(0.15 / 13)


# ---------------------------------------------------------------------------
# 5. rank_topics  --  the four edge cases from the spec (section 7.4)
# ---------------------------------------------------------------------------


class TestRankingEdgeCases:
    def test_never_attempted_topic_surfaces_near_the_top(self) -> None:
        """No mastery data, but the exploration bonus still floats it up."""
        blind_spot = _snapshot(topic_id=1, frequency_weight=0.05, attempts_count=0, days_ago=None)
        solid_and_recent = _snapshot(
            topic_id=2,
            skill_name="Percentages",
            frequency_weight=0.09,
            mastery_score=0.75,
            attempts_count=12,
            days_ago=0,
        )

        ranked = rank_topics([solid_and_recent, blind_spot], now=NOW)

        # blind spot: 0.05 * 0.6 + 0.15          = 0.18
        # solid:      0.09 * 0.25 + 0.15/13      = 0.0225 + 0.011538 = 0.034038
        assert ranked[0].topic_id == 1
        assert ranked[0].priority_score == pytest.approx(0.18)
        assert ranked[1].priority_score == pytest.approx(0.034038, abs=1e-6)

    def test_perfectly_mastered_recent_topic_sinks_to_the_bottom(self) -> None:
        mastered = _snapshot(
            topic_id=1, skill_name="Aced it", mastery_score=1.0, attempts_count=12, days_ago=0
        )
        shaky = _snapshot(
            topic_id=2, skill_name="Wobbly", mastery_score=0.35, attempts_count=8, days_ago=2
        )
        untouched = _snapshot(topic_id=3, skill_name="New", attempts_count=0, days_ago=None)

        ranked = rank_topics([mastered, shaky, untouched], now=NOW)

        assert ranked[-1].topic_id == 1
        # Only the exploration crumb keeps it above zero: 0.15 / 13.
        assert ranked[-1].priority_score == pytest.approx(0.15 / 13)

    def test_high_mastery_but_stale_is_pushed_back_up_by_decay(self) -> None:
        """The spaced-repetition property: forgetting resurfaces a strong topic."""
        common = dict(frequency_weight=0.08, mastery_score=0.90, attempts_count=8)
        fresh = _snapshot(topic_id=1, skill_name="Just reviewed", days_ago=0, **common)
        stale = _snapshot(topic_id=2, skill_name="Long ago", days_ago=30, **common)
        # A genuinely mediocre topic, practised today, same weight/volume.
        mediocre_fresh = _snapshot(
            topic_id=3,
            skill_name="So-so",
            frequency_weight=0.08,
            mastery_score=0.62,
            attempts_count=8,
            days_ago=0,
        )

        # fresh strong : 0.08 * (1 - 0.90) + 0.15/9 = 0.008   + 0.016667 = 0.024667
        # stale strong : decayed 0.90*e^-0.6 = 0.493931
        #                0.08 * (1 - 0.493931) + 0.15/9 = 0.040486 + 0.016667 = 0.057152
        # mediocre     : 0.08 * (1 - 0.62) + 0.15/9 = 0.0304  + 0.016667 = 0.047067
        fresh_score = rank_topics([fresh], now=NOW)[0].priority_score
        stale_score = rank_topics([stale], now=NOW)[0].priority_score
        mediocre_score = rank_topics([mediocre_fresh], now=NOW)[0].priority_score

        assert fresh_score == pytest.approx(0.024667, abs=1e-6)
        assert stale_score == pytest.approx(0.057152, abs=1e-6)

        # Freshly reviewed, the strong topic sits *below* the mediocre one...
        assert fresh_score < mediocre_score
        # ...but after a month of not touching it, decay lifts it back *above*.
        assert stale_score > mediocre_score

        ranked = rank_topics([fresh, stale, mediocre_fresh], now=NOW)
        assert [r.topic_id for r in ranked] == [2, 3, 1]

    def test_ties_are_broken_by_frequency_weight_descending(self) -> None:
        # Both: fw * urgency = 0.125, plus identical exploration bonus (n = 2).
        #   high: 0.5  * (1 - 0.75) = 0.5  * 0.25 = 0.125
        #   low:  0.25 * (1 - 0.50) = 0.25 * 0.50 = 0.125
        high_weight = _snapshot(
            topic_id=1,
            skill_name="Zebra",
            frequency_weight=0.5,
            mastery_score=0.75,
            attempts_count=2,
            days_ago=0,
        )
        low_weight = _snapshot(
            topic_id=2,
            skill_name="Aardvark",
            frequency_weight=0.25,
            mastery_score=0.5,
            attempts_count=2,
            days_ago=0,
        )

        for ordering in ([high_weight, low_weight], [low_weight, high_weight]):
            ranked = rank_topics(ordering, now=NOW)
            assert ranked[0].priority_score == ranked[1].priority_score  # a true tie
            assert ranked[0].topic_id == 1  # higher frequency_weight wins
            # ...and the skill name ("Zebra" > "Aardvark") did NOT decide it.


class TestRankTopicsMechanics:
    def test_limit_returns_the_top_n_only(self) -> None:
        snaps = [
            _snapshot(
                topic_id=i,
                skill_name=f"Skill {i}",
                frequency_weight=0.02 * i,
                mastery_score=0.3,
                attempts_count=5,
                days_ago=3,
            )
            for i in range(1, 6)
        ]
        assert len(rank_topics(snaps, now=NOW, limit=3)) == 3
        assert len(rank_topics(snaps, now=NOW, limit=99)) == 5
        assert rank_topics(snaps, now=NOW, limit=0) == []

    def test_scores_descend_through_the_whole_ranking(self) -> None:
        snaps = [
            _snapshot(topic_id=1, mastery_score=0.9, attempts_count=10, days_ago=0),
            _snapshot(topic_id=2, mastery_score=0.5, attempts_count=6, days_ago=5),
            _snapshot(topic_id=3, attempts_count=0, days_ago=None),
        ]
        scores = [r.priority_score for r in rank_topics(snaps, now=NOW)]
        assert scores == sorted(scores, reverse=True)

    def test_study_plan_defaults_to_five(self) -> None:
        snaps = [
            _snapshot(topic_id=i, skill_name=f"Skill {i}", attempts_count=4, days_ago=2)
            for i in range(1, 9)
        ]
        assert len(study_plan(snaps, now=NOW)) == 5

    def test_output_is_a_recommendation_with_a_full_breakdown(self) -> None:
        (rec,) = rank_topics([_snapshot(mastery_score=0.5, attempts_count=4, days_ago=10)], now=NOW)
        assert isinstance(rec, Recommendation)
        assert rec.days_since_practice == 10
        assert rec.decayed_mastery == pytest.approx(0.5 * math.exp(-0.2), abs=1e-9)
        assert rec.urgency == pytest.approx(1 - rec.decayed_mastery)
        assert rec.confidence == pytest.approx(0.8)  # 4 / 5


# ---------------------------------------------------------------------------
# 6. build_reason  --  the human-readable explanation string
# ---------------------------------------------------------------------------


class TestReasonString:
    def test_decayed_topic_matches_the_spec_example_format(self) -> None:
        # 0.41 * exp(-0.02 * 9) = 0.41 * 0.835270 = 0.342461 -> 34%
        reason = build_reason(
            section=Section.MATH,
            frequency_weight=0.08,
            mastery_score=0.41,
            decayed_mastery_value=0.41 * math.exp(-0.18),
            attempts_count=6,
            days_elapsed=9,
        )
        assert reason == (
            "Mastery 34% (decayed from 41%) · appears in ~8% of the Math section "
            "· last practiced 9 days ago"
        )

    def test_never_practiced_topic_is_flagged_as_an_exploration_pick(self) -> None:
        reason = build_reason(
            section=Section.MATH,
            frequency_weight=0.08,
            mastery_score=COLD_START_MASTERY,
            decayed_mastery_value=COLD_START_MASTERY,
            attempts_count=0,
            days_elapsed=None,
        )
        assert reason == (
            "Not yet practiced · appears in ~8% of the Math section · exploration pick"
        )

    def test_recently_practiced_topic_omits_the_decay_clause(self) -> None:
        reason = build_reason(
            section=Section.READING_WRITING,
            frequency_weight=0.12,
            mastery_score=0.62,
            decayed_mastery_value=0.62,
            attempts_count=5,
            days_elapsed=0,
        )
        assert reason == (
            "Mastery 62% · appears in ~12% of the Reading & Writing section · last practiced today"
        )

    def test_decay_too_small_to_change_the_rounded_percent_is_not_shown(self) -> None:
        # 0.20 * exp(-0.02) = 0.196039 -> still 20% once rounded, so no "(decayed from)".
        reason = build_reason(
            section=Section.MATH,
            frequency_weight=0.04,
            mastery_score=0.20,
            decayed_mastery_value=0.20 * math.exp(-0.02),
            attempts_count=4,
            days_elapsed=1,
        )
        assert reason == (
            "Mastery 20% · appears in ~4% of the Math section · last practiced yesterday"
        )


# ---------------------------------------------------------------------------
# 7. weighted_readiness  --  frequency-weighted mean of decayed mastery
# ---------------------------------------------------------------------------


class TestReadiness:
    def test_weighted_mean_of_fresh_scores(self) -> None:
        snaps = [
            _snapshot(
                topic_id=1, frequency_weight=0.6, mastery_score=1.0, attempts_count=8, days_ago=0
            ),
            _snapshot(
                topic_id=2, frequency_weight=0.4, mastery_score=0.5, attempts_count=8, days_ago=0
            ),
        ]
        # (0.6 * 1.0 + 0.4 * 0.5) / (0.6 + 0.4) = 0.8 / 1.0 = 0.8
        assert weighted_readiness(snaps, NOW) == pytest.approx(0.8)

    def test_decay_drags_the_headline_number_down(self) -> None:
        snaps = [
            _snapshot(
                topic_id=1, frequency_weight=0.6, mastery_score=1.0, attempts_count=8, days_ago=30
            ),
            _snapshot(
                topic_id=2, frequency_weight=0.4, mastery_score=0.5, attempts_count=8, days_ago=0
            ),
        ]
        # (0.6 * (1.0 * e^-0.6) + 0.4 * 0.5) / 1.0 = 0.6 * 0.548812 + 0.2 = 0.529287
        assert weighted_readiness(snaps, NOW) == pytest.approx(0.529287, abs=1e-6)

    def test_empty_input_is_zero_not_a_zero_division(self) -> None:
        assert weighted_readiness([], NOW) == 0.0

    def test_by_section_splits_the_roll_up(self) -> None:
        snaps = [
            _snapshot(
                topic_id=1,
                section=Section.MATH,
                frequency_weight=1.0,
                mastery_score=0.7,
                attempts_count=8,
                days_ago=0,
            ),
            _snapshot(
                topic_id=2,
                section=Section.READING_WRITING,
                frequency_weight=1.0,
                mastery_score=0.4,
                attempts_count=8,
                days_ago=0,
            ),
        ]
        by_section = readiness_by_section(snaps, NOW)
        assert by_section[Section.MATH] == pytest.approx(0.7)
        assert by_section[Section.READING_WRITING] == pytest.approx(0.4)
