"""Application configuration.

Values are read from environment variables (or a local ``.env`` file) with
defaults that work out of the box for local development. Keeping this in one
typed ``Settings`` object means swapping SQLite for Postgres later is a
one-line change to ``DATABASE_URL`` with no code edits.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    api_title: str = "SAT StudyPath API"
    api_version: str = "0.1.0"

    # SQLAlchemy URL. SQLite for dev; any SQLAlchemy-supported URL for prod.
    database_url: str = "sqlite:///./sat_studypath.db"

    # Origins allowed by CORS. Accepts a comma-separated string from the env.
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Guards POST /api/topics/seed (it wipes and regenerates data). On for local
    # dev; set false in any shared deployment.
    enable_dev_endpoints: bool = True

    @field_validator("database_url")
    @classmethod
    def _use_psycopg_driver(cls, url: str) -> str:
        """Managed Postgres providers hand out ``postgres://`` / ``postgresql://``
        URLs; SQLAlchemy needs the driver named explicitly for psycopg 3."""
        for prefix in ("postgres://", "postgresql://"):
            if url.startswith(prefix):
                return "postgresql+psycopg://" + url[len(prefix) :]
        return url

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
