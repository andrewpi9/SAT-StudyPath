"""End-to-end tests for the FastAPI layer (routing, schemas, wiring).

The scoring maths is covered exhaustively in test_mastery_engine.py; here we
check the endpoints project it correctly and handle bad input.
"""

from __future__ import annotations

import pytest
from sqlalchemy import func, select

from app.config import settings
from app.models.attempt import Attempt
from app.models.mastery import TopicMastery
from app.models.topic import Topic
from app.services.seeding import seed_database
from app.services.topics import load_taxonomy
from app.utils.time import utcnow


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
# POST /api/attempts/bulk  (CSV import)
# ---------------------------------------------------------------------------


def _csv_upload(client, text: str, name: str = "attempts.csv"):
    return client.post(
        "/api/attempts/bulk",
        files={"file": (name, text.encode(), "text/csv")},
    )


class TestBulkImport:
    def test_valid_csv_imports_every_row(self, seeded_client, db):
        csv = (
            "topic,correct,time_taken_seconds,difficulty,days_ago\n"
            "Linear functions,true,55,medium,3\n"
            "Percentages,false,90,hard,1\n"
            "Words in context,correct,40,easy,0\n"
        )
        before = db.scalar(select(func.count(Attempt.id)))
        r = _csv_upload(seeded_client, csv)

        assert r.status_code == 201
        assert r.json() == {"imported": 3, "failed": 0, "errors": []}
        assert db.scalar(select(func.count(Attempt.id))) == before + 3

    def test_bad_rows_are_reported_by_line_number_others_still_import(self, seeded_client):
        csv = (
            "topic,correct\n"
            "Linear functions,true\n"  # line 2 - ok
            "Nonexistent skill,true\n"  # line 3 - unknown topic
            "Percentages,maybe\n"  # line 4 - bad outcome
        )
        body = _csv_upload(seeded_client, csv).json()

        assert body["imported"] == 1
        assert body["failed"] == 2
        assert {e["row"] for e in body["errors"]} == {3, 4}
        assert "Nonexistent skill" in body["errors"][0]["message"]

    def test_optional_columns_default(self, seeded_client, db):
        # no time / difficulty / days_ago columns at all
        body = _csv_upload(seeded_client, "topic,correct\nPercentages,1\n").json()
        assert body["imported"] == 1
        newest = db.scalars(select(Attempt).order_by(Attempt.id.desc())).first()
        assert newest.time_taken_seconds == 60
        assert newest.difficulty == "medium"

    def test_days_ago_backdates_the_attempt(self, seeded_client, db):
        _csv_upload(seeded_client, "topic,correct,days_ago\nInferences,true,10\n")
        newest = db.scalars(select(Attempt).order_by(Attempt.id.desc())).first()
        assert 9 <= (utcnow() - newest.timestamp).days <= 10

    def test_all_invalid_rows_leaves_no_trace(self, seeded_client, db):
        before = db.scalar(select(func.count(Attempt.id)))
        body = _csv_upload(seeded_client, "topic,correct\nBogus,true\n").json()
        assert body == {"imported": 0, "failed": 1, "errors": body["errors"]}
        assert db.scalar(select(func.count(Attempt.id))) == before

    def test_non_csv_filename_is_rejected(self, seeded_client):
        assert _csv_upload(seeded_client, "topic,correct\n", name="notes.txt").status_code == 400

    def test_template_endpoint_serves_a_usable_csv(self, seeded_client):
        r = seeded_client.get("/api/attempts/template.csv")
        assert r.status_code == 200
        assert "text/csv" in r.headers["content-type"]
        # the template itself round-trips cleanly
        assert _csv_upload(seeded_client, r.text).json()["failed"] == 0


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
