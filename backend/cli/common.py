"""Small shared helpers used across CLI commands.

Kept deliberately thin: this module resolves/validates local paths and
manages the existing SQLAlchemy session lifecycle. It does not contain any
forensic logic — that all stays in backend/core, backend/parsers, etc.
"""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import typer
from rich.console import Console
from sqlalchemy.orm import Session

from backend.cli.exit_codes import ExitCode
from backend.cli.theme import error, get_console


def require_file(path: Path, console: Console | None = None) -> Path:
    """Resolve `path` to an absolute Path, or exit cleanly if it's missing.

    Windows paths (including ones with spaces, passed already-quoted by the
    shell) work fine here since we never re-split or shell out with them.
    """
    console = console or get_console()
    resolved = path.expanduser().resolve()
    if not resolved.exists():
        error(console, f"File not found: {resolved}")
        raise typer.Exit(code=ExitCode.FILE_NOT_FOUND)
    if not resolved.is_file():
        error(console, f"Not a file: {resolved}")
        raise typer.Exit(code=ExitCode.FILE_NOT_FOUND)
    return resolved


@contextmanager
def db_session() -> Iterator[Session]:
    """Yield a database session for the current settings.

    Deliberately builds its own engine/session factory per call via
    backend.db.database.create_session_factory(...) rather than importing
    that module's module-level SessionLocal. That module-level engine is
    bound once, to whatever DATABASE_URL was set the first time the module
    was imported in the process — correct for the long-running FastAPI app,
    but wrong for a CLI: a short-lived process should honor the DATABASE_URL
    in its own environment on every invocation, not whatever happened to be
    cached from an earlier import elsewhere. This also does not touch or
    disturb the FastAPI app's own get_db()/SessionLocal in any way.
    """
    from backend.config.settings import get_settings
    from backend.db.database import create_session_factory

    engine, session_factory = create_session_factory(get_settings().database_url)
    db = session_factory()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
        engine.dispose()


def fail(console: Console, message: str, code: int) -> "typer.Exit":
    error(console, message)
    return typer.Exit(code=code)
