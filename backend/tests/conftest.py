import os
import tempfile
from pathlib import Path
import pytest
from sqlalchemy import event
from sqlalchemy.engine import Engine
from backend.config.settings import get_settings

_GLOBAL_TEST_ROOT = Path(tempfile.gettempdir()) / "dvr_forensics_pytest_session"
_GLOBAL_TEST_ROOT.mkdir(parents=True, exist_ok=True)


def pytest_configure(config):
    """
    Hook executed before any test modules or application modules are imported.
    Sets default environment variables to temporary paths so import-time singletons
    (like engine and SessionLocal in backend.db.database) bind to SQLite from the start.
    Also registers a session-wide guard against non-SQLite connections.
    """
    orig_root = _GLOBAL_TEST_ROOT / "storage" / "original"
    work_root = _GLOBAL_TEST_ROOT / "storage" / "working_copies"
    extr_root = _GLOBAL_TEST_ROOT / "storage" / "extracted"
    db_file = _GLOBAL_TEST_ROOT / "session_forensics.db"

    orig_root.mkdir(parents=True, exist_ok=True)
    work_root.mkdir(parents=True, exist_ok=True)
    extr_root.mkdir(parents=True, exist_ok=True)

    os.environ["ORIGINAL_EVIDENCE_ROOT"] = str(orig_root)
    os.environ["WORKING_COPY_ROOT"] = str(work_root)
    os.environ["EXTRACTED_MEDIA_ROOT"] = str(extr_root)
    os.environ["DATABASE_URL"] = f"sqlite:///{db_file}"

    get_settings.cache_clear()

    @event.listens_for(Engine, "do_connect")
    def _guard_non_sqlite(dialect, conn_rec, cargs, cparams):
        if dialect.name != "sqlite":
            raise RuntimeError(
                f"Prohibited non-SQLite database connection during test run: dialect={dialect.name}"
            )


@pytest.fixture(autouse=True)
def isolate_storage(tmp_path, monkeypatch):
    """
    Autouse fixture to isolate test runs from the real backend/storage directory
    and remote/configured database.
    Monkeypatches ORIGINAL_EVIDENCE_ROOT, WORKING_COPY_ROOT, EXTRACTED_MEDIA_ROOT,
    and DATABASE_URL to temporary paths and clears the get_settings LRU cache.
    """
    orig_root = tmp_path / "storage" / "original"
    work_root = tmp_path / "storage" / "working_copies"
    extr_root = tmp_path / "storage" / "extracted"
    db_file = tmp_path / "test_forensics.db"
    
    orig_root.mkdir(parents=True, exist_ok=True)
    work_root.mkdir(parents=True, exist_ok=True)
    extr_root.mkdir(parents=True, exist_ok=True)
    
    monkeypatch.setenv("ORIGINAL_EVIDENCE_ROOT", str(orig_root))
    monkeypatch.setenv("WORKING_COPY_ROOT", str(work_root))
    monkeypatch.setenv("EXTRACTED_MEDIA_ROOT", str(extr_root))
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file}")
    
    get_settings.cache_clear()
    try:
        yield
    finally:
        get_settings.cache_clear()
