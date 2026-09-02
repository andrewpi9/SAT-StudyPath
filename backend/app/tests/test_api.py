"""End-to-end tests for the FastAPI layer (routing, auth, schemas, wiring).

The scoring maths is covered exhaustively in test_mastery_engine.py; here we
check the endpoints project it correctly, enforce auth, and handle bad input.
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
from app.tests.conftest import TEST_EMAIL
from app.utils.time import utcnow


@pytest.fixture
def seeded_client(authed_client, user_id, db):
    seed_database(db, user_id=user_id, rng_seed=42)
    return authed_client


def _a_topic_id(db) -> int:
    return db.scalar(select(Topic.id).order_by(Topic.id))


def _csv_upload(client, text: str, name: str = "attempts.csv"):
    return client.post("/api/attempts/bulk", files={"file": (name, text.encode(), "text/csv")})


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


class TestAuth:
    def test_signup_returns_a_working_token(self, client):
        r = client.post("/api/auth/signup", json={"email": "a@b.com", "password": "hunter2!!"})
        assert r.status_code == 201
        body = r.json()
        assert body["token_type"] == "bearer"
        assert body["user"]["email"] == "a@b.com"

        me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"})
        assert me.json()["email"] == "a@b.com"

    def test_signup_rejects_duplicate_email(self, client):
        client.post("/api/auth/signup", json={"email": "dup@b.com", "password": "hunter2!!"})
        r = client.post("/api/auth/signup", json={"email": "DUP@b.com", "password": "hunter2!!"})
        assert r.status_code == 409

    def test_signup_rejects_short_password(self, client):
        assert (
            client.post(
                "/api/auth/signup", json={"email": "a@b.com", "password": "short"}
            ).status_code
            == 422
        )

    def test_login_wrong_password_is_401(self, client, user_id):
        assert (
            client.post(
                "/api/auth/login", json={"email": TEST_EMAIL, "password": "wrong-password"}
            ).status_code
            == 401
        )

    def test_protected_endpoints_require_a_token(self, client):
        for path in ("/api/mastery", "/api/study-plan", "/api/progress"):
            assert client.get(path).status_code == 401
        assert (
            client.post(
                "/api/attempts",
                json={
                    "topic_id": 1,
                    "correct": True,
                    "time_taken_seconds": 5,
                    "difficulty": "easy",
                },
            ).status_code
            == 401
        )

    def test_a_garbage_token_is_401(self, client):
        assert (
            client.get("/api/mastery", headers={"Authorization": "Bearer not.a.jwt"}).status_code
            == 401
        )

    def test_public_endpoints_need_no_token(self, client, db):
        load_taxonomy(db)
        db.commit()
        assert client.get("/api/topics").status_code == 200
        assert client.get(f"/api/resources/{_a_topic_id(db)}").status_code == 200

    def test_two_users_have_isolated_data(self, client, db):
        load_taxonomy(db)
        db.commit()
        topic_id = _a_topic_id(db)

        tokens = {}
        for email in ("u1@b.com", "u2@b.com"):
            tokens[email] = client.post(
                "/api/auth/signup", json={"email": email, "password": "password123"}
            ).json()["access_token"]

        h1 = {"Authorization": f"Bearer {tokens['u1@b.com']}"}
        for _ in range(4):
            client.post(
                "/api/attempts",
                json={
                    "topic_id": topic_id,
                    "correct": False,
                    "time_taken_seconds": 30,
                    "difficulty": "hard",
                },
                headers=h1,
            )

        u1 = next(
            t
            for t in client.get("/api/mastery", headers=h1).json()["topics"]
            if t["topic_id"] == topic_id
        )
        h2 = {"Authorization": f"Bearer {tokens['u2@b.com']}"}
        u2 = next(
            t
            for t in client.get("/api/mastery", headers=h2).json()["topics"]
            if t["topic_id"] == topic_id
        )

        assert u1["attempts_count"] == 4
        assert u2["attempts_count"] == 0  # untouched by user 1's practice


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
        assert [t["section"] for t in body] == ["Math"] * 20 + ["ReadingWriting"] * 15

    def test_seed_endpoint_populates_the_current_user(self, authed_client):
        r = authed_client.post("/api/topics/seed", json={"rng_seed": 1, "target_attempts": 120})
        assert r.status_code == 201
        body = r.json()
        assert body["topics_created"] == 35
        assert body["reset"] is True
        assert body["attempts_created"] == pytest.approx(120, abs=40)
        assert authed_client.get("/api/mastery").json()["overall_readiness"] > 0

    def test_seed_endpoint_works_with_no_body(self, authed_client):
        assert authed_client.post("/api/topics/seed").status_code == 201

    def test_seed_endpoint_can_be_disabled(self, authed_client, monkeypatch):
        monkeypatch.setattr(settings, "enable_dev_endpoints", False)
        assert authed_client.post("/api/topics/seed").status_code == 403

    def test_seed_endpoint_requires_auth(self, client):
        assert client.post("/api/topics/seed").status_code == 401


# ---------------------------------------------------------------------------
# POST /api/attempts
# ---------------------------------------------------------------------------


class TestLogAttempt:
    def test_correct_answer_raises_mastery_and_returns_the_update(self, seeded_client, user_id, db):
        topic_id = _a_topic_id(db)
        before = db.get(TopicMastery, (user_id, topic_id))
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
            {"difficulty": "trivial"},
            {"time_taken_seconds": 0},
            {"time_taken_seconds": 10_000},
            {"topic_id": "abc"},
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


class TestBulkImport:
    def test_valid_csv_imports_every_row(self, seeded_client, user_id, db):
        csv = (
            "topic,correct,time_taken_seconds,difficulty,days_ago\n"
            "Linear functions,true,55,medium,3\n"
            "Percentages,false,90,hard,1\n"
            "Words in context,correct,40,easy,0\n"
        )
        before = db.scalar(select(func.count(Attempt.id)).where(Attempt.user_id == user_id))
        r = _csv_upload(seeded_client, csv)

        assert r.status_code == 201
        assert r.json() == {"imported": 3, "failed": 0, "errors": []}
        assert (
            db.scalar(select(func.count(Attempt.id)).where(Attempt.user_id == user_id))
            == before + 3
        )

    def test_bad_rows_are_reported_by_line_number_others_still_import(self, seeded_client):
        csv = "topic,correct\nLinear functions,true\nNonexistent skill,true\nPercentages,maybe\n"
        body = _csv_upload(seeded_client, csv).json()

        assert body["imported"] == 1
        assert body["failed"] == 2
        assert {e["row"] for e in body["errors"]} == {3, 4}
        assert "Nonexistent skill" in body["errors"][0]["message"]

    def test_optional_columns_default(self, seeded_client, db):
        body = _csv_upload(seeded_client, "topic,correct\nPercentages,1\n").json()
        assert body["imported"] == 1
        newest = db.scalars(select(Attempt).order_by(Attempt.id.desc())).first()
        assert newest.time_taken_seconds == 60
        assert newest.difficulty == "medium"

    def test_days_ago_backdates_the_attempt(self, seeded_client, db):
        _csv_upload(seeded_client, "topic,correct,days_ago\nInferences,true,10\n")
        newest = db.scalars(select(Attempt).order_by(Attempt.id.desc())).first()
        assert 9 <= (utcnow() - newest.timestamp).days <= 10

    def test_all_invalid_rows_leaves_no_trace(self, seeded_client, user_id, db):
        before = db.scalar(select(func.count(Attempt.id)).where(Attempt.user_id == user_id))
        body = _csv_upload(seeded_client, "topic,correct\nBogus,true\n").json()
        assert body == {"imported": 0, "failed": 1, "errors": body["errors"]}
        assert db.scalar(select(func.count(Attempt.id)).where(Attempt.user_id == user_id)) == before

    def test_non_csv_filename_is_rejected(self, seeded_client):
        assert _csv_upload(seeded_client, "topic,correct\n", name="notes.txt").status_code == 400

    def test_requires_auth(self, client):
        assert _csv_upload(client, "topic,correct\nPercentages,1\n").status_code == 401

    def test_template_endpoint_serves_a_usable_csv(self, seeded_client):
        r = seeded_client.get("/api/attempts/template.csv")
        assert r.status_code == 200
        assert "text/csv" in r.headers["content-type"]
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

    def test_fresh_account_is_not_an_error(self, authed_client):
        body = authed_client.get("/api/mastery").json()
        assert body["topics"] == []
        assert body["overall_readiness"] == 0.0


# ---------------------------------------------------------------------------
# GET /api/resources/{topic_id}
# ---------------------------------------------------------------------------


class TestResources:
    def test_every_topic_has_resources(self, seeded_client, db):
        topic_id = _a_topic_id(db)
        body = seeded_client.get(f"/api/resources/{topic_id}").json()
        assert len(body) == 2
        assert {r["type"] for r in body} == {"video", "article"}
        assert all(r["url"].startswith("https://") for r in body)
        assert all(r["topic_id"] == topic_id for r in body)

    def test_unknown_topic_is_404(self, seeded_client):
        assert seeded_client.get("/api/resources/999999").status_code == 404

    def test_seeding_twice_does_not_duplicate(self, authed_client, user_id, db):
        seed_database(db, user_id=user_id, rng_seed=1)
        seed_database(db, user_id=user_id, rng_seed=1)
        topic_id = _a_topic_id(db)
        assert len(authed_client.get(f"/api/resources/{topic_id}").json()) == 2

    def test_study_plan_items_carry_their_resources(self, seeded_client):
        items = seeded_client.get("/api/study-plan").json()["items"]
        assert all(len(item["resources"]) == 2 for item in items)
        assert items[0]["resources"][0]["title"]


# ---------------------------------------------------------------------------
# GET /api/progress
# ---------------------------------------------------------------------------


class TestProgress:
    def test_series_length_and_shape(self, seeded_client):
        body = seeded_client.get("/api/progress", params={"days": 30}).json()
        assert body["range_days"] == 30
        assert len(body["points"]) == 30

        days = [p["day"] for p in body["points"]]
        assert days == sorted(days)
        for p in body["points"]:
            for key in ("overall_readiness", "math_readiness", "reading_writing_readiness"):
                assert 0.0 <= p[key] <= 1.0

    def test_last_point_matches_current_readiness(self, seeded_client):
        progress = seeded_client.get("/api/progress", params={"days": 40}).json()
        mastery = seeded_client.get("/api/mastery").json()
        assert progress["points"][-1]["overall_readiness"] == pytest.approx(
            mastery["overall_readiness"], abs=0.02
        )

    def test_readiness_trends_upward_over_the_seeded_history(self, seeded_client):
        points = seeded_client.get("/api/progress", params={"days": 40}).json()["points"]
        assert points[-1]["overall_readiness"] > points[0]["overall_readiness"]

    def test_fresh_account_with_taxonomy_is_flat_at_cold_start(self, authed_client, db):
        load_taxonomy(db)
        db.commit()
        points = authed_client.get("/api/progress", params={"days": 7}).json()["points"]
        assert all(p["overall_readiness"] == pytest.approx(0.4) for p in points)

    @pytest.mark.parametrize("days", [0, -1, 400])
    def test_days_out_of_bounds_is_422(self, seeded_client, days):
        assert seeded_client.get("/api/progress", params={"days": days}).status_code == 422


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
        assert new_rank[top["topic_id"]] > 0
