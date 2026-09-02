# SAT StudyPath

Personalized SAT study-path generator. Ingests a student's practice results by
**topic** (never by real question content) and produces a ranked "what to study
next" plan using an actual adaptive algorithm — recency-weighted mastery scoring,
forgetting-curve decay, and real digital-SAT topic-frequency weighting.

Built by a former SAT tutor (60+ videos, 5M+ views) as a portfolio piece. The
full write-up — including a plain-English "How the recommendation algorithm
works" section — lands in milestone 7.

> **Status:** milestone 3 of 7 complete — data model, seed script, the full
> recommendation engine (EWMA mastery + forgetting-curve decay + priority
> ranking) with a hand-computed pytest suite, and the FastAPI endpoints on top
> of it. Frontend UI is next.

## Layout

```
backend/
  app/algorithm/   the recommendation engine — pure, DB-free, hand-tested functions
    mastery.py     EWMA update on each attempt          (spec 7.1)
    decay.py       forgetting-curve decay at read time  (spec 7.2)
    priority.py    priority score + reason strings       (spec 7.3)
    readiness.py   frequency-weighted roll-up
  app/models/      SQLAlchemy 2.0 ORM
  app/schemas/     Pydantic request/response models
  app/services/    ORM <-> algorithm glue; the one write path (record_attempt)
  app/routers/     FastAPI endpoints (one module per resource)
  app/tests/       test_mastery_engine.py is the one to read
frontend/          React + Vite + TypeScript + Tailwind (UI wired up in milestones 4-7)
```

## API

Run `uvicorn app.main:app --reload` and open `http://localhost:8000/docs`.

| method | path | purpose |
|---|---|---|
| `GET`  | `/api/topics` | the full skill taxonomy |
| `POST` | `/api/topics/seed` | dev only — (re)load taxonomy + synthetic history |
| `POST` | `/api/attempts` | log one attempt; returns the topic's updated mastery |
| `GET`  | `/api/mastery` | every topic's mastery/decay/confidence + readiness roll-up |
| `GET`  | `/api/study-plan?limit=5` | ranked recommendations with reason strings |

## Run the backend

Requires Python 3.11+ (3.13 recommended).

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python -m app.seed          # create the DB, taxonomy, and a synthetic history
uvicorn app.main:app --reload   # http://localhost:8000/api/health , /docs
pytest                      # algorithm + seed tests
```

<details>
<summary>Using <a href="https://docs.astral.sh/uv/">uv</a> instead</summary>

```bash
cd backend
uv venv && uv pip install -r requirements.txt
uv run python -m app.seed
uv run uvicorn app.main:app --reload
uv run pytest
```
</details>

## Run the frontend

```bash
cd frontend
npm install
npm run dev                 # http://localhost:5173 (proxies /api to :8000)
```

## Data / content policy

No real College Board question text, answer choices, or passages appear anywhere
in this project. Only skill tags, correctness, timing, and difficulty are stored.
Topic-frequency weights are approximate and tutor-informed (see
`backend/app/data/taxonomy.py`), not scraped from any proprietary source.
