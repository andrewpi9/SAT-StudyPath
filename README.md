# SAT StudyPath

SAT StudyPath takes your practice results by topic and tells you what to study next. It ranks every skill by how much score you could lose right now, and it explains each choice in plain English.

The ranking runs on a real algorithm, not a checklist. It tracks how well you know each skill, fades that number over time when you stop practicing, and weights everything by how often the skill shows up on the test.

<p align="center">
  <img src="docs/study_plan.png" alt="Today's Study Plan, a ranked list of skills with a plain English reason for each" width="49%">
  <img src="docs/dashboard_dark.png" alt="Mastery Dashboard, a readiness trend and a heatmap of every skill colored by decayed mastery" width="49%">
</p>

## Why I built this

I ran an SAT tutoring channel. Sixty plus videos, over five million views. The question students asked most was never "how do I solve this problem." It was "what should I study next?"

Most prep tools answer that badly. They give you a checklist or a raw accuracy percentage. Neither one handles the two things that actually move a score.

Skills fade. You nailed linear functions three weeks ago and have not touched them since. That is not the same as nailing them yesterday. Your lifetime accuracy number treats both cases as identical.

Topics are not worth the same. Missing 20 percent of linear equation questions costs you far more than missing 20 percent of a topic that shows up twice per test.

StudyPath handles both. The engine lives in `backend/app/algorithm/`. It is five modules of pure functions with a test suite that works the math out by hand. If you read one section of this file, read the next one.

## How the recommendation algorithm works

Three ideas, applied in order. The numbers below are the live constants from the code.

### Mastery is a moving average, not lifetime accuracy

Your skill changes as you study. That is the point. A plain average of every attempt you have ever made lets a rough first week hold down a topic you have since mastered.

So each attempt nudges the estimate a fixed fraction of the way toward that result.

```
outcome     = 1.0 if correct else 0.0
new_mastery = old_mastery + 0.3 * (outcome - old_mastery)   # learning rate 0.3
```

Recent attempts carry the most weight. Old ones fade but never get dropped. A topic with no attempts starts at 0.4, a little below the middle, because with no evidence you should assume you are not ready. A separate confidence value climbs to 1.0 over your first five attempts. That lets the interface tell "34 percent" apart from "34 percent, and we have only seen two questions."

### Forgetting curve decay, applied when the app reads the number

Memory decays over time. Ebbinghaus modeled it as exponential decay. StudyPath applies the same thing.

```
decayed_mastery = mastery_score * exp(-0.02 * days_since_practice)
```

A week untouched costs about 13 percent of a skill. A month costs about 45 percent.

The stored score never moves because of decay. It always means "how well you did the last time you practiced." Decay is a lens the app lays over it at read time. Practice the topic again and you write a fresh score and reset the clock, so a short review session wins most of that ground back.

### Priority is points at risk plus a nudge toward blind spots

```
urgency           = 1 - decayed_mastery
exploration_bonus = 0.15 / (1 + attempts_count)
priority_score    = frequency_weight * urgency + exploration_bonus
```

`frequency_weight * urgency` is the expected points at risk. A shaky skill that covers a lot of the test beats a shaky skill that barely appears. `frequency_weight` is each skill's share of its section. I seeded it from College Board's published domain weights plus my own read of the question mix across released tests. It is in `backend/app/data/taxonomy.py`.

The exploration bonus is a separate term. It surfaces a topic you have never touched, even though there is no evidence it is weak. You cannot fix a blind spot you never find. The bonus is 0.15 at zero attempts and drops fast once you start practicing.

Every recommendation comes with a reason string built from the same numbers.

> Mastery 36 percent, down from 47 percent. Shows up in about 9 percent of the Reading and Writing section. Last practiced 13 days ago.

### Spaced repetition falls out of this for free

Take a skill sitting at 90 percent mastery.

Practice it today and the decayed mastery stays at 90 percent, so the priority score is about 0.025. Leave it alone for 30 days and the decayed mastery drops to 49 percent, so the priority score climbs to about 0.057.

The priority more than doubles with no new data. That is pure decay. A fresh skill at 62 percent mastery scores about 0.047, so after a month of neglect the strong stale skill passes the mediocre fresh one. Nobody wrote a "remind me to review" rule. It comes straight out of decay and urgency. There is a test for it, `test_high_mastery_but_stale_is_pushed_back_up_by_decay`.

### The readiness trend is rebuilt, not stored

`GET /api/progress` does not read a table of daily snapshots. There is no such table. It takes your whole attempt history, replays the moving average forward, and records the readiness adjusted for decay at the end of each day. See `backend/app/algorithm/progress.py`. It runs in time proportional to your attempts plus the days in the range.

A dip in the chart during a study break is the forgetting curve working against zero new practice. Same mechanism, seen over time.

## Architecture

React, Vite, and TypeScript on the frontend. FastAPI and SQLAlchemy on the backend. SQLite for local dev, Postgres in production, one line in config to switch.

The code splits into layers.

`backend/app/algorithm/` holds the engine. Every function is pure. It takes plain values and an explicit "now" and returns a number or a dataclass. No database, no clock, no server needed to test it. The modules are mastery, decay, priority, readiness, and progress.

`backend/app/services/` connects the database to the algorithm. Two functions matter. `record_attempt` is the only write path, so the update rule lives in exactly one place. `topic_snapshots` is the only projection from database rows into algorithm input.

`backend/app/routers/` holds thin HTTP handlers. Every route that touches your data depends on `get_current_user` from `backend/app/auth.py`.

`frontend/src/` has pages, components, an api folder with a typed fetch client, and an auth folder with the token store.

Multiple people can sign up. Auth uses JWT bearer tokens. There are three pages. Study Plan is the ranked list with links per topic and a jump straight to practice. Dashboard shows the readiness trend and the mastery heatmap. Log Attempt takes one question at a time or a CSV of a whole session.

## Running it

You need Python 3.11 or newer and Node 20 or newer. A clean clone runs in a couple of minutes.

Backend, at `http://localhost:8000`.

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python -m app.seed
uvicorn app.main:app --reload
```

The seed creates the demo account. Email `demo@studypath.app`, password `demopassword`. Or click "Try the demo account" on the login screen. A new signup starts empty.

You can use uv instead.

<details><summary>uv commands</summary>

```bash
cd backend
uv venv && uv pip install -r requirements.txt
uv run python -m app.seed
uv run uvicorn app.main:app --reload
```
</details>

Frontend, at `http://localhost:5173`.

```bash
cd frontend
npm install
npm run dev
```

Tests.

```bash
cd backend && pytest
```

That runs 118 tests. Read `backend/app/tests/test_mastery_engine.py` first. It has 52 cases with the arithmetic written out in comments next to each assertion. They cover every ranking edge case. A topic you never attempted still surfaces through exploration. A topic you aced today sinks. A strong topic you have not touched in weeks comes back up. Ties break by frequency weight.

## API

Every data route needs a bearer token from `/api/auth/login` or `/api/auth/signup`. `/api/topics` and `/api/resources/{topic_id}` are public.

`GET /api/topics` returns the full taxonomy of 35 skills.

`GET /api/mastery` returns every skill's mastery, decay, and confidence, plus the readiness rollup.

`GET /api/study-plan?limit=5` returns the ranked recommendations with reason strings and study links.

`GET /api/progress?days=30` returns readiness per day, replayed from your history.

`GET /api/resources/{topic_id}` returns study links for one topic.

`POST /api/attempts` logs one attempt and returns the updated mastery.

`POST /api/attempts/bulk` imports a CSV. Get the format from `GET /api/attempts/template.csv`.

`POST /api/topics/seed` regenerates a synthetic history for the current user. Dev only.

## Data and content policy

No real College Board question text, answer choices, or passages appear anywhere in this project. The database stores skill tags, correctness, timing, and difficulty. Nothing else.

The seed script writes synthetic attempts. A row reads `topic=Linear Functions, correct=false, 47s`. There is never any question content. The frequency weights are rough and come from my tutoring experience, not from anything proprietary.

## Deployment

The config is in the repo. `render.yaml` sets up a FastAPI web service and a free Postgres database. `backend/Dockerfile` builds the API. `frontend/vercel.json` handles SPA routing and proxies `/api` to the backend.

Moving from SQLite to Postgres means changing `DATABASE_URL`. The psycopg driver gets picked automatically. Postgres URLs get normalized in `backend/app/config.py`. The driver sits in `backend/requirements-prod.txt` so a local install stays small. Set `SEED_DEMO_ON_STARTUP` to true and the app recreates the demo account on first boot.

1. API. On Render, choose New, then Blueprint, then this repo. It builds the web service and the database and generates `JWT_SECRET`. Set `CORS_ORIGINS` to the frontend URL once you have it.
2. Frontend. On Vercel, import the repo and set the root directory to `frontend`. Edit the `/api` rewrite in `vercel.json` to point at the Render URL.

## What I'd build next

A calibrated scaled score. Map the 0 to 1 readiness number onto the 400 to 1600 range using real concordance data.

Refresh tokens. The access token lasts a week right now. Add a rotating refresh token and cut the lifetime.

Adaptive difficulty. Recommend which difficulty band to practice per topic, using the accuracy data the app already logs.

Alembic migrations. `create_all` works for a fresh deploy. A service with real users needs versioned schema changes.
