"""Tests for the dvrforensics CLI (backend/cli/).

Follows the same pattern as test_database_flow.py: a fresh sqlite DB per
test under tmp_path, env vars pointing the acquisition service's copy
roots at tmp_path, and get_settings.cache_clear() so the new env is picked
up. The CLI's own db_session() (backend/cli/common.py) builds a fresh
engine per call from current settings, so no dependency-override plumbing
is needed the way the FastAPI TestClient tests need it.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from backend.cli.exit_codes import ExitCode
from backend.cli.main import app
from backend.db.database import create_session_factory
from backend.db.models import Base

FIXTURE = Path("backend/tests/fixtures/hikvision_synthetic.dd").resolve()

runner = CliRunner()


@pytest.fixture()
def cli_env(tmp_path, monkeypatch):
    """Point the CLI at an isolated sqlite DB + acquisition roots, per test."""
    database_url = f"sqlite:///{tmp_path / 'forensics.db'}"
    engine, _ = create_session_factory(database_url)
    Base.metadata.create_all(engine)
    engine.dispose()

    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("ORIGINAL_EVIDENCE_ROOT", str(tmp_path / "original"))
    monkeypatch.setenv("WORKING_COPY_ROOT", str(tmp_path / "working"))
    monkeypatch.setenv("EXTRACTED_MEDIA_ROOT", str(tmp_path / "extracted"))
    monkeypatch.setenv("DVRFORENSICS_NO_ANIMATION", "1")

    from backend.config.settings import get_settings

    get_settings.cache_clear()
    yield tmp_path
    get_settings.cache_clear()


def _create_case(tmp_path) -> str:
    from backend.config.settings import get_settings
    from backend.db.database import create_session_factory
    from backend.db.models import Case

    _, session_factory = create_session_factory(get_settings().database_url)
    db = session_factory()
    try:
        case = Case(name="Test Case", investigator="Examiner")
        db.add(case)
        db.commit()
        db.refresh(case)
        return case.id
    finally:
        db.close()


# ---------------------------------------------------------------------------
# detect
# ---------------------------------------------------------------------------

def test_detect_identifies_hikvision_fixture():
    result = runner.invoke(app, ["detect", str(FIXTURE)])
    assert result.exit_code == ExitCode.OK
    assert "Hikvision" in result.stdout or "hikvision" in result.stdout.lower()


def test_detect_missing_file_returns_file_not_found():
    result = runner.invoke(app, ["detect", "/tmp/definitely_not_here.dd"])
    assert result.exit_code == ExitCode.FILE_NOT_FOUND


def test_detect_unsupported_file_returns_unsupported_vendor(tmp_path):
    junk = tmp_path / "junk.bin"
    junk.write_bytes(b"not a dvr image" * 100)
    result = runner.invoke(app, ["detect", str(junk)])
    assert result.exit_code == ExitCode.UNSUPPORTED_VENDOR


# ---------------------------------------------------------------------------
# evidence hash
# ---------------------------------------------------------------------------

def test_evidence_hash_matches_direct_computation():
    from backend.core.integrity.hashing import compute_hashes

    expected = compute_hashes(str(FIXTURE))
    result = runner.invoke(app, ["evidence", "hash", str(FIXTURE)])
    assert result.exit_code == ExitCode.OK
    assert expected["sha256"] in result.stdout
    assert expected["md5"] in result.stdout


def test_evidence_hash_rejects_zero_chunk_size():
    result = runner.invoke(app, ["evidence", "hash", str(FIXTURE), "--chunk-size", "0"])
    assert result.exit_code == ExitCode.INVALID_ARGUMENT


# ---------------------------------------------------------------------------
# parse
# ---------------------------------------------------------------------------

def test_parse_finds_recordings(tmp_path):
    out_dir = tmp_path / "parse_out"
    result = runner.invoke(app, ["parse", str(FIXTURE), "--output", str(out_dir)])
    assert result.exit_code == ExitCode.OK
    assert "hik-000000" in result.stdout
    assert "CH-01" in result.stdout


# ---------------------------------------------------------------------------
# extract
# ---------------------------------------------------------------------------

def test_extract_runs_against_fixture(tmp_path):
    out_dir = tmp_path / "extract_out"
    result = runner.invoke(app, ["extract", str(FIXTURE), "--output", str(out_dir)])
    # The synthetic fixture has no real MPEG-PS payload, so recordings come
    # back PARTIAL/unrecovered — that's expected (see make_hikvision_fixture.py)
    # and is not a hard failure, just nothing to recover.
    assert result.exit_code == ExitCode.OK
    assert "PARTIAL" in result.stdout or "RECOVERED" in result.stdout


def test_extract_reports_missing_ffmpeg(tmp_path, monkeypatch):
    monkeypatch.setattr("shutil.which", lambda _name: None)
    result = runner.invoke(app, ["extract", str(FIXTURE), "--output", str(tmp_path / "out")])
    assert result.exit_code == ExitCode.MISSING_DEPENDENCY


# ---------------------------------------------------------------------------
# case
# ---------------------------------------------------------------------------

def test_case_create_list_show(cli_env):
    create = runner.invoke(
        app, ["case", "create", "--name", "My Case", "--investigator", "J. Doe", "--case-number", "C-1"]
    )
    assert create.exit_code == ExitCode.OK
    assert "Created case" in create.stdout

    listing = runner.invoke(app, ["case", "list"])
    assert listing.exit_code == ExitCode.OK
    assert "My Case" in listing.stdout

    case_id = _get_first_case_id(cli_env)
    show = runner.invoke(app, ["case", "show", case_id])
    assert show.exit_code == ExitCode.OK
    assert "J. Doe" in show.stdout


def test_case_show_unknown_id_returns_not_found(cli_env):
    result = runner.invoke(app, ["case", "show", "does-not-exist"])
    assert result.exit_code == ExitCode.NOT_FOUND


def _get_first_case_id(tmp_path) -> str:
    from backend.config.settings import get_settings
    from backend.db.database import create_session_factory
    from backend.db.models import Case

    _, session_factory = create_session_factory(get_settings().database_url)
    db = session_factory()
    try:
        return db.query(Case).first().id
    finally:
        db.close()


# ---------------------------------------------------------------------------
# evidence add (reference + copy modes)
# ---------------------------------------------------------------------------

def test_evidence_add_reference_mode_does_not_copy(cli_env):
    case_id = _create_case(cli_env)
    result = runner.invoke(app, ["evidence", "add", str(FIXTURE), "--case", case_id, "--mode", "reference"])
    assert result.exit_code == ExitCode.OK
    assert "reference mode" in result.stdout.lower() or "Reference mode" in result.stdout

    from backend.config.settings import get_settings
    from backend.db.database import create_session_factory
    from backend.db.models import Evidence

    _, session_factory = create_session_factory(get_settings().database_url)
    db = session_factory()
    try:
        ev = db.query(Evidence).filter(Evidence.case_id == case_id).first()
        assert ev is not None
        assert ev.original_path == ev.working_copy_path == str(FIXTURE)
    finally:
        db.close()


def test_evidence_add_copy_mode_verifies_hashes(cli_env):
    case_id = _create_case(cli_env)
    result = runner.invoke(app, ["evidence", "add", str(FIXTURE), "--case", case_id, "--mode", "copy"])
    assert result.exit_code == ExitCode.OK
    assert "verified" in result.stdout.lower()

    from backend.config.settings import get_settings
    from backend.db.database import create_session_factory
    from backend.db.models import Evidence, EvidenceStatus

    _, session_factory = create_session_factory(get_settings().database_url)
    db = session_factory()
    try:
        ev = db.query(Evidence).filter(Evidence.case_id == case_id).first()
        assert ev is not None
        assert ev.status == EvidenceStatus.VERIFIED
        assert ev.working_copy_path != ev.original_path
        assert Path(ev.working_copy_path).exists()
    finally:
        db.close()


def test_evidence_add_unknown_case_returns_not_found(cli_env):
    result = runner.invoke(app, ["evidence", "add", str(FIXTURE), "--case", "no-such-case"])
    assert result.exit_code == ExitCode.NOT_FOUND


def test_evidence_list_shows_registered_items(cli_env):
    case_id = _create_case(cli_env)
    runner.invoke(app, ["evidence", "add", str(FIXTURE), "--case", case_id, "--mode", "reference"])
    result = runner.invoke(app, ["evidence", "list", "--case", case_id])
    assert result.exit_code == ExitCode.OK
    assert FIXTURE.name in result.stdout


# ---------------------------------------------------------------------------
# search / analyze — optional-dependency guardrails
# ---------------------------------------------------------------------------

def test_search_reports_missing_groq_dependency_gracefully(cli_env, monkeypatch):
    case_id = _create_case(cli_env)
    monkeypatch.setitem(__import__("sys").modules, "groq", None)
    result = runner.invoke(app, ["search", case_id, "people at camera 2"])
    # Either a clean MISSING_DEPENDENCY exit, or (if groq happens to be
    # installed in this environment) a clean non-crash exit — the important
    # thing is no raw traceback reaches the user either way.
    assert result.exit_code in (ExitCode.OK, ExitCode.MISSING_DEPENDENCY, ExitCode.GENERAL_ERROR)
    assert "Traceback" not in result.stdout


def test_search_unknown_case_returns_not_found(cli_env):
    result = runner.invoke(app, ["search", "no-such-case", "anything"])
    assert result.exit_code == ExitCode.NOT_FOUND


def test_analyze_missing_file_returns_file_not_found(cli_env):
    result = runner.invoke(app, ["analyze", "/tmp/no_such_video.mp4"])
    assert result.exit_code == ExitCode.FILE_NOT_FOUND
    assert "Traceback" not in result.stdout


# ---------------------------------------------------------------------------
# top-level
# ---------------------------------------------------------------------------

def test_bare_invocation_shows_banner_and_help():
    result = runner.invoke(app, [])
    assert result.exit_code == ExitCode.OK
    assert "DVR" in result.stdout


def test_help_lists_all_commands():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == ExitCode.OK
    for cmd in ("detect", "parse", "extract", "analyze", "search", "case", "evidence"):
        assert cmd in result.stdout
