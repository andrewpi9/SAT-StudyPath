"""FastAPI application entrypoint.

    uvicorn app.main:app --reload

Interactive API docs at /docs once running.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.routers import attempts, mastery, progress, resources, study_plan, topics


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    init_db()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title=settings.api_title, version=settings.api_version, lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health", tags=["meta"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(topics.router)
    app.include_router(attempts.router)
    app.include_router(mastery.router)
    app.include_router(study_plan.router)
    app.include_router(progress.router)
    app.include_router(resources.router)

    return app


app = create_app()
