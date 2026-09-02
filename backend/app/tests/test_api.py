"""End-to-end tests for the FastAPI layer (routing, schemas, wiring).

The scoring maths is covered exhaustively in test_mastery_engine.py; here we
check the endpoints project it correctly and handle bad input.
"""

from __future__ import annotations

import pytest
from sqlalchemy import select

from app.config import settings
from app.models.mastery import TopicMastery
from app.models.topic import Topic
from app.services.seeding import seed_database
from app.services.topics import load_taxonomy


@pytest.fixture
def seeded_client(client, db):
    seed_database(db, rng_seed=42)
    return client


def _a_topic_id(db) -> int:
    return db.scalar(select(Topic.id).order_by(Topic.id))


# ---------------------------------------------------------------------------
# GET /api/topics  and  POST /api/topics/seed
# ---------------------------------------------------------------------------


class TestTopics:
    def test_lists_the_full_taxonomy(self, client, db):
        load_taxonomy(db)
        db.commit()

        body = client.get("/api/topics").json()
        assert len(body) == 35
        assert {t["section"] for t in body} == {"Math", "ReadingWriting"}
        assert all(0 < t["frequency_weight"] < 1 for t in body)
        # Math topics sort before Reading & Writing.
        assert [t["section"] for t in body] == ["Math"] * 20 + ["ReadingWriting"] * 15

    def test_seed_endpoint_populates_the_database(self, client):
        r = client.post("/api/topics/seed", json={"rng_seed": 1, "target_attempts": 120})
        assert r.status_code == 201

        body = r.json()
        assert body["topics_created"] == 35
        assert body["reset"] is True
        assert body["attempts_created"] == pytest.approx(120, abs=40)
        assert len(client.get("/api/topics").json()) == 35

    def test_seed_endpoint_works_with_no_body(self, client):
        assert client.post("/api/topics/seed").status_code == 201

    def test_seed_endpoint_can_be_disabled(self, client, monkeypatch):
        monkeypatch.setattr(settings, "enable_dev_endpoints", False)
        assert client.post("/api/topics/seed").status_code == 403


# ---------------------------------------------------------------------------
# POST /api/attempts
# ---------------------------------------------------------------------------


class TestLogAttempt:
    def test_correct_answer_raises_mastery_and_returns_the_update(self, seeded_client, db):
        topic_id = _a_topic_id(db)
        before = db.get(TopicMastery, topic_id)
        before_score, before_count = before.mastery_score, before.attempts_count

        r = seeded_client.post(
            "/api/attempts",
            json={
                "topic_id": topic_id,
                "correct": True,
                "time_taken_seconds": 45,
                "difficulty": "medium",
            },
        )
        assert r.status_code == 201

        body = r.json()
        assert body["attempt"]["topic_id"] == topic_id
        assert body["attempt"]["correct"] is True
        assert body["attempt"]["difficulty"] == "medium"
        assert body["mastery"]["attempts_count"] == before_count + 1
        assert body["mastery"]["mastery_score"] > before_score
        assert body["mastery"]["decayed_mastery"] <= body["mastery"]["mastery_score"] + 1e-9
        assert body["mastery"]["days_since_practice"] == 0

    def test_unknown_topic_returns_404(self, seeded_client):
        r = seeded_client.post(
            "/api/attempts",
            json={
                "topic_id": 999_999,
                "correct": True,
                "time_taken_seconds": 30,
                "difficulty": "easy",
            },
        )
        assert r.status_code == 404

    @pytest.mark.parametrize(
        "patch",
        [
            {"difficulty": "trivial"},  # not a valid enum member
            {"time_taken_seconds": 0},  # must be > 0
            {"time_taken_seconds": 10_000},  # must be <= 3600
            {"topic_id": "abc"},  # not an int
        ],
    )
    def test_invalid_payload_returns_422(self, seeded_client, db, patch):
        payload = {
            "topic_id": _a_topic_id(db),
            "correct": True,
            "time_taken_seconds": 40,
            "difficulty": "medium",
        }
        payload.update(patch)
        assert seeded_client.post("/api/attempts", json=payload).status_code == 422


# ---------------------------------------------------------------------------
# GET /api/mastery
# ---------------------------------------------------------------------------


class TestMasteryOverview:
    def test_shape_and_invariants(self, seeded_client):
        body = seeded_client.get("/api/mastery").json()

        assert 0.0 <= body["overall_readiness"] <= 1.0
        assert set(body["section_readiness"]) == {"Math", "ReadingWriting"}
        assert len(body["topics"]) == 35
        assert [t["section"] for t in body["topics"]] == ["Math"] * 20 + ["ReadingWriting"] * 15

        for t in body["topics"]:
            assert 0.0 <= t["decayed_mastery"] <= t["mastery_score"] + 1e-9
            assert 0.0 <= t["confidence"] <= 1.0

    def test_never_practiced_topic_reports_nulls(self, seeded_client):
        topics = seeded_client.get("/api/mastery").json()["topics"]
        untouched = [t for t in topics if t["attempts_count"] == 0]
        assert untouched
        for t in untouched:
            assert t["last_practiced"] is None
            assert t["days_since_practice"] is None

    def test_empty_database_is_not_an_error(self, client):
        body = client.get("/api/mastery").json()
        assert body["topics"] == []
        assert body["overall_readiness"] == 0.0


# ---------------------------------------------------------------------------
# GET /api/study-plan
# ---------------------------------------------------------------------------


class TestStudyPlan:
    def test_defaults_to_five_ranked_items_with_reasons(self, seeded_client):
        body = seeded_client.get("/api/study-plan").json()

        assert body["limit"] == 5
        assert len(body["items"]) == 5
        scores = [i["priority_score"] for i in body["items"]]
        assert scores == sorted(scores, reverse=True)
        assert all(i["reason"] for i in body["items"])

    def test_limit_query_param(self, seeded_client):
        assert len(seeded_client.get("/api/study-plan", params={"limit": 12}).json()["items"]) == 12

    @pytest.mark.parametrize("limit", [0, -1, 36, 999])
    def test_limit_out_of_bounds_is_422(self, seeded_client, limit):
        assert seeded_client.get("/api/study-plan", params={"limit": limit}).status_code == 422

    def test_practising_the_top_topic_demotes_it(self, seeded_client):
        top = seeded_client.get("/api/study-plan", params={"limit": 35}).json()["items"][0]

        for _ in range(6):
            seeded_client.post(
                "/api/attempts",
                json={
                    "topic_id": top["topic_id"],
                    "correct": True,
                    "time_taken_seconds": 40,
                    "difficulty": "medium",
                },
            )

        after = seeded_client.get("/api/study-plan", params={"limit": 35}).json()["items"]
        new_rank = {item["topic_id"]: i for i, item in enumerate(after)}
        assert new_rank[top["topic_id"]] > 0  # no longer first
