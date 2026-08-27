"""Runtime settings for local development and Supabase-backed deployments."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv


def _sqlalchemy_database_url(url: str) -> str:
    """Normalise Supabase's Postgres connection URL for SQLAlchemy/psycopg."""
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url.removeprefix("postgresql://")
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url.removeprefix("postgres://")
    return url


@dataclass(frozen=True)
class Settings:
    database_url: str
    original_evidence_root: Path
    working_copy_root: Path
    extracted_media_root: Path
    derived_media_provider: str
    supabase_url: str | None
    supabase_anon_key: str | None
    supabase_jwt_secret: str | None
    auth_required: bool
    cors_origins: list[str]


@lru_cache
def get_settings() -> Settings:
    project_root = Path(__file__).resolve().parents[2]
    load_dotenv(project_root / ".env")
    storage_root = project_root / "backend" / "storage"
    return Settings(
        database_url=_sqlalchemy_database_url(
            os.getenv("DATABASE_URL", "sqlite:///backend/forensics.db")
        ),
        # Original evidence stays in a controlled local/Object-Lock evidence store.
        # Supabase Storage is deliberately only a derived-media destination.
        original_evidence_root=Path(os.getenv("ORIGINAL_EVIDENCE_ROOT", storage_root / "original")),
        working_copy_root=Path(os.getenv("WORKING_COPY_ROOT", storage_root / "working_copies")),
        extracted_media_root=Path(os.getenv("EXTRACTED_MEDIA_ROOT", storage_root / "extracted")),
        derived_media_provider=os.getenv("DERIVED_MEDIA_PROVIDER", "local"),
        supabase_url=os.getenv("SUPABASE_URL"),
        supabase_anon_key=os.getenv("SUPABASE_ANON_KEY"),
        supabase_jwt_secret=os.getenv("SUPABASE_JWT_SECRET"),
        auth_required=os.getenv("AUTH_REQUIRED", "false").lower() == "true",
        cors_origins=[
            origin.strip()
            for origin in os.getenv("CORS_ORIGINS", "http://localhost:5174,http://127.0.0.1:5174").split(",")
            if origin.strip()
        ],
    )
