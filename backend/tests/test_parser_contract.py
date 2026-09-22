"""
Contract and characterization tests for all registered DVR parsers.
"""

import hashlib
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
import pytest
from typer.testing import CliRunner
from fastapi.testclient import TestClient

from backend.parsers.registry import PARSERS, ParserManager
from backend.parsers.common.base import BaseDVRParser, ParseError
from backend.parsers.hikvision.parser import HikvisionParser
from backend.db.services import _json_safe, _detection_json_safe, persist_parse_result
from backend.db.models import Base, Case, Evidence, EvidenceStatus
from backend.db.database import create_session_factory, get_db
from backend.cli.main import app as cli_app
from backend.api.main import app as fastapi_app
from backend.config.settings import get_settings


def compute_sha256(file_path: str | Path) -> str:
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def snapshot_tree(root: Path) -> dict[Path, float]:
    """Capture snapshot of relative paths and mtimes in a tree."""
    return {p.relative_to(root): p.stat().st_mtime for p in root.rglob("*") if p.is_file()}


@pytest.fixture
def empty_file(tmp_path) -> Path:
    p = tmp_path / "empty.bin"
    p.write_bytes(b"")
    return p


@pytest.fixture
def random_1kb_file(tmp_path) -> Path:
    p = tmp_path / "random_1kb.bin"
    p.write_bytes(os.urandom(1024))
    return p


@pytest.fixture
def truncated_hikvision_file(tmp_path) -> Path:
    p = tmp_path / "truncated_hikvision.bin"
    # Less than 0x360 bytes (e.g. 500 bytes) with partial signature bytes
    p.write_bytes(b"\x00" * 0x210 + b"HIKVISION@HANGZHOU" + b"\x00" * 10)
    return p


@pytest.mark.parametrize("parser", PARSERS, ids=lambda p: p.vendor_name)
class TestParserContract:
    def test_detect_never_raises_on_nonexistent_path(self, parser: BaseDVRParser, tmp_path):
        nonexistent = str(tmp_path / "does_not_exist_file.dd")
        matched, conf, info = parser.detect(nonexistent)
        assert matched is False
        assert conf == 0.0
        assert info == {}

    def test_detect_never_raises_on_empty_file(self, parser: BaseDVRParser, empty_file: Path):
        matched, conf, info = parser.detect(str(empty_file))
        assert matched is False
        assert conf == 0.0
        assert info == {}

    def test_detect_never_raises_on_random_bytes(self, parser: BaseDVRParser, random_1kb_file: Path):
        matched, conf, info = parser.detect(str(random_1kb_file))
        # Non-matching data returns False, 0.0, {}
        assert matched is False
        assert conf == 0.0
        assert info == {}

    def test_detect_never_raises_on_truncated_fixture(self, parser: BaseDVRParser, truncated_hikvision_file: Path):
        matched, conf, info = parser.detect(str(truncated_hikvision_file))
        assert matched is False
        assert conf == 0.0
        assert info == {}

    def test_detect_and_validate_leave_sha256_unchanged(self, parser: BaseDVRParser, random_1kb_file: Path):
        initial_hash = compute_sha256(random_1kb_file)
        parser.detect(str(random_1kb_file))
        assert compute_sha256(random_1kb_file) == initial_hash

        parser.validate(str(random_1kb_file))
        assert compute_sha256(random_1kb_file) == initial_hash

    def test_parse_writes_only_inside_output_directory(self, parser: BaseDVRParser, tmp_path, monkeypatch, random_1kb_file: Path):
        work_sandbox = tmp_path / "sandbox"
        work_sandbox.mkdir()
        out_dir = work_sandbox / "parser_output"
        out_dir.mkdir()

        monkeypatch.setenv("ORIGINAL_EVIDENCE_ROOT", str(work_sandbox / "original"))
        monkeypatch.setenv("WORKING_COPY_ROOT", str(work_sandbox / "working"))
        monkeypatch.setenv("EXTRACTED_MEDIA_ROOT", str(work_sandbox / "extracted"))

        initial_snapshot = snapshot_tree(tmp_path)

        result = parser.parse(str(random_1kb_file), str(out_dir))
        assert result is not None

        # Compare file tree after parsing: all newly created files must be under out_dir
        final_snapshot = snapshot_tree(tmp_path)
        new_or_modified = set(final_snapshot.keys()) - set(initial_snapshot.keys())

        out_rel = out_dir.relative_to(tmp_path)
        for rel_path in new_or_modified:
            assert str(rel_path).startswith(str(out_rel)), f"File created outside output directory: {rel_path}"


class TestParserManagerDetection:
    FIXTURES_DIR = Path("backend/tests/fixtures")

    def test_hikvision_fixtures_detection(self):
        manager = ParserManager()

        normal_dd = self.FIXTURES_DIR / "hikvision_normal.dd"
        if normal_dd.exists():
            parser, conf, info = manager.detect(str(normal_dd))
            assert parser is not None
            assert parser.vendor_name == "hikvision"
            assert conf == 0.9

        deleted_dd = self.FIXTURES_DIR / "hikvision_deleted.dd"
        if deleted_dd.exists():
            parser, conf, info = manager.detect(str(deleted_dd))
            assert parser is not None
            # Master block is present on hikvision_deleted.dd, so it matches hikvision
            assert parser.vendor_name == "hikvision"
            assert conf == 0.9

        synthetic_dd = self.FIXTURES_DIR / "hikvision_synthetic.dd"
        if synthetic_dd.exists():
            parser, conf, info = manager.detect(str(synthetic_dd))
            assert parser is not None
            assert parser.vendor_name == "hikvision"
            assert conf == 0.9

    def test_wiped_master_block_falls_through_to_carver(self, tmp_path):
        normal_dd = self.FIXTURES_DIR / "hikvision_normal.dd"
        if not normal_dd.exists():
            pytest.skip("hikvision_normal.dd fixture not present")

        wiped_dd = tmp_path / "hikvision_wiped_mb.dd"
        data = bytearray(normal_dd.read_bytes())
        # Wipe master block (0x200 to 0x360)
        data[0x200:0x360] = b"\x00" * (0x360 - 0x200)
        wiped_dd.write_bytes(data)

        manager = ParserManager()
        parser, conf, info = manager.detect(str(wiped_dd))
        assert parser is not None
        assert parser.vendor_name == "generic_dvr_carver"
        assert conf == 0.65

    def test_e01_and_split_returns_unsupported_format(self, tmp_path):
        e01_file = tmp_path / "sample.E01"
        e01_file.write_bytes(b"EVF\x09\x0d\x0a\xff\x00" + b"\x00" * 500)

        manager = ParserManager()
        result = manager.parse(str(e01_file), str(tmp_path / "out"))
        assert result.success is False
        assert result.error_code == ParseError.UNSUPPORTED_FORMAT
        assert any("E01" in err or "reassembly" in err for err in result.errors)

    def test_detect_candidates_fault_tolerant_on_raising_parser(self, monkeypatch, tmp_path):
        synthetic_dd = self.FIXTURES_DIR / "hikvision_synthetic.dd"
        if not synthetic_dd.exists():
            pytest.skip("hikvision_synthetic.dd not found")

        # Monkeypatch first parser to raise RuntimeError
        manager = ParserManager()
        failing_parser = PARSERS[0]

        def raising_detect(path):
            raise RuntimeError("Simulated parser corruption")

        monkeypatch.setattr(failing_parser, "detect", raising_detect)

        parser, conf, info, candidates = manager.detect_candidates(str(synthetic_dd))
        failing_cand = next(c for c in candidates if c["vendor"] == failing_parser.vendor_name)
        assert failing_cand["matched"] is False
        assert failing_cand["confidence"] == 0.0
        assert "RuntimeError: Simulated parser corruption" in failing_cand["info"]["error"]


class TestHeimVisionCharacterization:
    VPS_MARKER = b"\x00\x00\x00\x01\x40"

    def test_heimvision_detects_two_vps_in_first_8mib(self, tmp_path):
        hevc_file = tmp_path / "test_stream.dat"
        # Place 2 VPS markers within first 8 MiB (e.g. at 1 MiB and 2 MiB)
        data = bytearray(b"\x00" * (3 * 1024 * 1024))
        data[1024 * 1024 : 1024 * 1024 + len(self.VPS_MARKER)] = self.VPS_MARKER
        data[2 * 1024 * 1024 : 2 * 1024 * 1024 + len(self.VPS_MARKER)] = self.VPS_MARKER
        hevc_file.write_bytes(data)

        manager = ParserManager()
        parser, conf, info = manager.detect(str(hevc_file))
        assert parser is not None
        assert parser.vendor_name == "heimvision"
        assert conf == 0.75
        assert info.get("vps_markers_found") == 2

    def test_heimvision_ignores_vps_after_8mib(self, tmp_path):
        hevc_file = tmp_path / "test_stream_late.dat"
        # Place VPS markers after 8 MiB (e.g. at 9 MiB and 10 MiB)
        size = 11 * 1024 * 1024
        data = bytearray(b"\x00" * size)
        data[9 * 1024 * 1024 : 9 * 1024 * 1024 + len(self.VPS_MARKER)] = self.VPS_MARKER
        data[10 * 1024 * 1024 : 10 * 1024 * 1024 + len(self.VPS_MARKER)] = self.VPS_MARKER
        hevc_file.write_bytes(data)

        manager = ParserManager()
        parser, conf, info = manager.detect(str(hevc_file))
        # HeimVision should not match because its detect() only reads the first 8 MiB
        assert parser is None or parser.vendor_name != "heimvision"


class TestDetectionPersistenceAndJsonSafety:
    def test_json_safe_reverts_to_utf8_decode(self):
        """Verify _json_safe maintains its original behavior (utf-8 decoding with replacement)."""
        dt = datetime(2026, 9, 19, 18, 0, 0, tzinfo=timezone.utc)
        test_dict = {
            "bytes_val": b"hello\x00\x01world",
            "datetime_val": dt,
            "nested": {
                "list_val": [b"test_bytes", dt],
                "int_val": 42,
            },
        }
        sanitized = _json_safe(test_dict)
        assert sanitized["bytes_val"] == b"hello\x00\x01world".decode("utf-8", errors="replace")
        assert sanitized["datetime_val"] == "2026-09-19T18:00:00+00:00"
        assert sanitized["nested"]["list_val"][0] == "test_bytes"
        assert sanitized["nested"]["list_val"][1] == "2026-09-19T18:00:00+00:00"

    def test_detection_json_safe_sanitizes_candidates_and_detection_info(self):
        """Verify _detection_json_safe converts bytes to hex, datetimes to ISO, and sets to lists."""
        dt = datetime(2026, 9, 19, 18, 0, 0, tzinfo=timezone.utc)
        test_dict = {
            "bytes_val": b"\x00\x01\x02\xba",
            "datetime_val": dt,
            "set_val": {"h264", "hevc"},
            "nested": {
                "list_val": [b"\xaa\xbb", dt],
                "int_val": 42,
            },
        }
        sanitized = _detection_json_safe(test_dict)
        assert sanitized["bytes_val"] == "000102ba"
        assert sanitized["datetime_val"] == "2026-09-19T18:00:00+00:00"
        assert isinstance(sanitized["set_val"], list)
        assert set(sanitized["set_val"]) == {"h264", "hevc"}
        assert sanitized["nested"]["list_val"][0] == "aabb"
        assert sanitized["nested"]["list_val"][1] == "2026-09-19T18:00:00+00:00"

    def test_raw_metadata_preservation_hikvision_synthetic(self, tmp_path):
        """Device.raw_metadata and Recording.raw_metadata for hikvision_synthetic.dd match expected HEAD schema."""
        database_url = f"sqlite:///{tmp_path / 'meta_test.db'}"
        engine, session_factory = create_session_factory(database_url)
        Base.metadata.create_all(engine)

        with session_factory() as db:
            case = Case(name="Meta Case", investigator="Investigator")
            db.add(case)
            db.commit()

            evidence = Evidence(
                case_id=case.id,
                original_filename="hikvision_synthetic.dd",
                original_path=str(tmp_path / "hikvision_synthetic.dd"),
                working_copy_path=str(tmp_path / "hikvision_synthetic.dd"),
                status=EvidenceStatus.ACQUIRED,
            )
            db.add(evidence)
            db.commit()

            fixture_path = Path("backend/tests/fixtures/hikvision_synthetic.dd")
            if not fixture_path.exists():
                pytest.skip("hikvision_synthetic.dd not found")

            manager = ParserManager()
            parse_result = manager.parse(str(fixture_path), str(tmp_path / "parsed"))
            assert parse_result.success is True

            device, recs = persist_parse_result(db, evidence, parse_result)
            db.refresh(evidence)

            # Assert Device.raw_metadata is identical to expected HEAD dictionary
            assert device.raw_metadata == {"vendor": "hikvision", "version": "HIK.2011.03.08"}

            # Assert Recording.raw_metadata for all 3 recordings matches parse_result and HEAD values
            rec_metadata = [r.raw_metadata for r in recs]
            assert rec_metadata == [r.raw_metadata for r in parse_result.recordings]
            assert rec_metadata == [
                {"channel": 1, "offset": 5242880},
                {"channel": 2, "offset": 6291456},
                {"channel": 1, "offset": 7340032},
            ]

    def test_hikvision_extract_recordings_without_master_block_fails(self, tmp_path):
        """Hikvision extract_recordings returns error when master block is None."""
        synthetic_dd = Path("backend/tests/fixtures/hikvision_synthetic.dd")
        if not synthetic_dd.exists():
            pytest.skip("hikvision_synthetic.dd not found")

        parser = HikvisionParser()
        res = parser.extract_recordings(str(synthetic_dd), str(tmp_path), [], None)
        assert res.success is False
        assert res.error_code == ParseError.EXTRACTION_FAILED
        assert res.errors == ["Master block unavailable; cannot determine data block size"]

    def test_persistence_stores_detection_confidence_and_candidates(self, tmp_path):
        database_url = f"sqlite:///{tmp_path / 'test_evidence.db'}"
        engine, session_factory = create_session_factory(database_url)
        Base.metadata.create_all(engine)

        db = session_factory()
        try:
            case = Case(name="Test Case", investigator="Investigator")
            db.add(case)
            db.commit()

            evidence = Evidence(
                case_id=case.id,
                original_filename="synthetic.dd",
                original_path=str(tmp_path / "synthetic.dd"),
                working_copy_path=str(tmp_path / "synthetic.dd"),
                status=EvidenceStatus.ACQUIRED,
            )
            db.add(evidence)
            db.commit()

            fixture_path = Path("backend/tests/fixtures/hikvision_synthetic.dd")
            if not fixture_path.exists():
                pytest.skip("hikvision_synthetic.dd not found")

            manager = ParserManager()
            parse_result = manager.parse(str(fixture_path), str(tmp_path / "parsed"))
            assert parse_result.success is True

            device, recs = persist_parse_result(db, evidence, parse_result)
            db.refresh(evidence)

            assert evidence.vendor == "hikvision"
            assert evidence.detection_confidence == 0.9
            assert evidence.detection_info is not None
            assert evidence.detection_info["selected_parser"] == "hikvision"
            assert "candidates" in evidence.detection_info
            assert len(evidence.detection_info["candidates"]) == len(PARSERS)

            # Check that candidate info is JSON-safe
            candidates = evidence.detection_info["candidates"]
            hik_candidate = next(c for c in candidates if c["vendor"] == "hikvision")
            assert hik_candidate["matched"] is True
            assert hik_candidate["confidence"] == 0.9
        finally:
            db.close()


class TestCliRunnerAndMigrationAutomated:
    runner = CliRunner()
    FIXTURES_DIR = Path("backend/tests/fixtures")

    def test_cli_detect_all_non_tty(self):
        synthetic_dd = self.FIXTURES_DIR / "hikvision_synthetic.dd"
        if not synthetic_dd.exists():
            pytest.skip("hikvision_synthetic.dd not found")

        result = self.runner.invoke(cli_app, ["detect", "--all", str(synthetic_dd)])
        assert result.exit_code == 0
        assert "Candidate Parser Evaluations" in result.stdout
        assert "HikvisionParser" in result.stdout
        assert "Hex Dump" in result.stdout
        assert "Printable ASCII Strings" in result.stdout

    def test_automated_migration_upgrade_and_evidence_loading(self, tmp_path, monkeypatch):
        """Build SQLite DB at 20260828_01, insert row, upgrade to head, and assert GET /evidence."""
        db_path = tmp_path / "migration_test.db"
        database_url = f"sqlite:///{db_path}"

        monkeypatch.setenv("DATABASE_URL", database_url)
        monkeypatch.setenv("ORIGINAL_EVIDENCE_ROOT", str(tmp_path / "original"))
        monkeypatch.setenv("WORKING_COPY_ROOT", str(tmp_path / "working"))
        monkeypatch.setenv("EXTRACTED_MEDIA_ROOT", str(tmp_path / "extracted"))
        get_settings.cache_clear()

        # Step 1: Run alembic upgrade to 20260828_01
        env = os.environ.copy()
        env["DATABASE_URL"] = database_url
        env["PYTHONPATH"] = "."
        subprocess.run(["alembic", "upgrade", "20260828_01"], check=True, env=env, capture_output=True)

        # Step 2: Insert raw evidence row at 20260828_01 schema level using raw SQL
        import uuid
        from sqlalchemy import text
        engine, session_factory = create_session_factory(database_url)
        case_id = str(uuid.uuid4())
        evidence_id = str(uuid.uuid4())
        with engine.begin() as conn:
            conn.execute(
                text("INSERT INTO cases (id, name, investigator, status, created_at) VALUES (:id, :name, :inv, 'open', :now)"),
                {"id": case_id, "name": "Migration Case", "inv": "Agent", "now": datetime.utcnow()},
            )
            conn.execute(
                text(
                    "INSERT INTO evidence (id, case_id, original_filename, original_path, working_copy_path, status, acquired_at, parse_warnings, parse_errors) "
                    "VALUES (:id, :case_id, :fn, :op, :wp, 'ACQUIRED', :now, '[]', '[]')"
                ),
                {
                    "id": evidence_id,
                    "case_id": case_id,
                    "fn": "pre_migration.dd",
                    "op": str(tmp_path / "pre_migration.dd"),
                    "wp": str(tmp_path / "pre_migration.dd"),
                    "now": datetime.utcnow(),
                },
            )

        # Step 3: Upgrade to head (20260830_01)
        subprocess.run(["alembic", "upgrade", "head"], check=True, env=env, capture_output=True)

        # Step 4: Load via API and assert detection fields
        def test_db_override():
            db = session_factory()
            try:
                yield db
            finally:
                db.close()

        fastapi_app.dependency_overrides[get_db] = test_db_override
        try:
            with TestClient(fastapi_app) as client:
                res = client.get(f"/evidence/{evidence_id}")
                assert res.status_code == 200
                data = res.json()
                assert data["id"] == evidence_id
                assert data["detection_confidence"] is None
                assert data["detection_info"] in (None, {})
        finally:
            fastapi_app.dependency_overrides.clear()
            get_settings.cache_clear()

    def test_parse_synthetic_persists_device_metadata(self, tmp_path, monkeypatch):
        """After POST /evidence/{id}/parse on hikvision_synthetic.dd, Device row has firmware_version 'HIK.2011.03.08' and vendor 'hikvision'."""
        synthetic_dd = self.FIXTURES_DIR / "hikvision_synthetic.dd"
        if not synthetic_dd.exists():
            pytest.skip("hikvision_synthetic.dd not found")

        database_url = f"sqlite:///{tmp_path / 'regression.db'}"
        engine, session_factory = create_session_factory(database_url)
        Base.metadata.create_all(engine)

        def test_db():
            db = session_factory()
            try:
                yield db
            finally:
                db.close()

        monkeypatch.setenv("DATABASE_URL", database_url)
        monkeypatch.setenv("ORIGINAL_EVIDENCE_ROOT", str(tmp_path / "original"))
        monkeypatch.setenv("WORKING_COPY_ROOT", str(tmp_path / "working"))
        monkeypatch.setenv("EXTRACTED_MEDIA_ROOT", str(tmp_path / "extracted"))
        get_settings.cache_clear()
        fastapi_app.dependency_overrides[get_db] = test_db

        try:
            with TestClient(fastapi_app) as client:
                case_res = client.post("/cases", json={"name": "Device Reg Case", "investigator": "Forensic Agent"})
                assert case_res.status_code == 201
                case_id = case_res.json()["id"]

                ev_res = client.post(f"/cases/{case_id}/evidence", json={"source_path": str(synthetic_dd.resolve())})
                assert ev_res.status_code == 201
                evidence_id = ev_res.json()["id"]

                parse_res = client.post(f"/evidence/{evidence_id}/parse")
                assert parse_res.status_code == 200

                from backend.db.models import Device
                with session_factory() as session:
                    device = session.query(Device).filter(Device.evidence_id == evidence_id).first()
                    assert device is not None
                    assert device.vendor == "hikvision"
                    assert device.firmware_version == "HIK.2011.03.08"
        finally:
            fastapi_app.dependency_overrides.clear()
            get_settings.cache_clear()

    def test_extract_preserves_detection_metadata(self, tmp_path, monkeypatch):
        """After POST /evidence/{id}/extract, detection_confidence and detection_info from parse are unchanged, not overwritten."""
        synthetic_dd = self.FIXTURES_DIR / "hikvision_synthetic.dd"
        if not synthetic_dd.exists():
            pytest.skip("hikvision_synthetic.dd not found")

        database_url = f"sqlite:///{tmp_path / 'extract_regression.db'}"
        engine, session_factory = create_session_factory(database_url)
        Base.metadata.create_all(engine)

        def test_db():
            db = session_factory()
            try:
                yield db
            finally:
                db.close()

        monkeypatch.setenv("DATABASE_URL", database_url)
        monkeypatch.setenv("ORIGINAL_EVIDENCE_ROOT", str(tmp_path / "original"))
        monkeypatch.setenv("WORKING_COPY_ROOT", str(tmp_path / "working"))
        monkeypatch.setenv("EXTRACTED_MEDIA_ROOT", str(tmp_path / "extracted"))
        get_settings.cache_clear()
        fastapi_app.dependency_overrides[get_db] = test_db

        try:
            with TestClient(fastapi_app) as client:
                case_res = client.post("/cases", json={"name": "Extract Reg Case", "investigator": "Forensic Agent"})
                assert case_res.status_code == 201
                case_id = case_res.json()["id"]

                ev_res = client.post(f"/cases/{case_id}/evidence", json={"source_path": str(synthetic_dd.resolve())})
                assert ev_res.status_code == 201
                evidence_id = ev_res.json()["id"]

                parse_res = client.post(f"/evidence/{evidence_id}/parse")
                assert parse_res.status_code == 200
                parsed_data = parse_res.json()
                parse_confidence = parsed_data["detection_confidence"]
                parse_info = parsed_data["detection_info"]
                assert parse_confidence == 0.9
                assert parse_info is not None

                extract_res = client.post(f"/evidence/{evidence_id}/extract")
                assert extract_res.status_code == 200
                extracted_data = extract_res.json()

                assert extracted_data["detection_confidence"] == parse_confidence
                assert extracted_data["detection_info"] == parse_info
        finally:
            fastapi_app.dependency_overrides.clear()
            get_settings.cache_clear()


class TestParserPerformanceAndShortCircuit:
    FIXTURES_DIR = Path("backend/tests/fixtures")

    def test_short_circuit_on_hikvision_normal_does_not_call_carver(self, monkeypatch):
        normal_dd = self.FIXTURES_DIR / "hikvision_normal.dd"
        if not normal_dd.exists():
            pytest.skip("hikvision_normal.dd not found")

        carver = next(p for p in PARSERS if p.vendor_name == "generic_dvr_carver")
        carver_detect_calls = 0
        original_carver_detect = carver.detect

        def spy_carver_detect(path):
            nonlocal carver_detect_calls
            carver_detect_calls += 1
            return original_carver_detect(path)

        monkeypatch.setattr(carver, "detect", spy_carver_detect)

        manager = ParserManager()
        parser, conf, info, candidates = manager.detect_candidates(str(normal_dd), exhaustive=False)

        assert carver_detect_calls == 0
        assert parser is not None
        assert parser.vendor_name == "hikvision"
        assert conf == 0.90

        # Assert skipped candidates
        skipped_cands = [c for c in candidates if c.get("skipped")]
        assert len(skipped_cands) == 3
        for c in skipped_cands:
            assert c["matched"] is None
            assert c["confidence"] is None
            assert c["skipped"] == "outscored by hikvision"

    def test_exhaustive_true_calls_all_four_parsers(self, monkeypatch):
        normal_dd = self.FIXTURES_DIR / "hikvision_normal.dd"
        if not normal_dd.exists():
            pytest.skip("hikvision_normal.dd not found")

        detect_counts = {p.vendor_name: 0 for p in PARSERS}
        for p in PARSERS:
            orig = p.detect
            def make_spy(parser_vendor, orig_fn):
                def spy(path):
                    detect_counts[parser_vendor] += 1
                    return orig_fn(path)
                return spy
            monkeypatch.setattr(p, "detect", make_spy(p.vendor_name, orig))

        manager = ParserManager()
        parser, conf, info, candidates = manager.detect_candidates(str(normal_dd), exhaustive=True)

        assert parser is not None
        assert parser.vendor_name == "hikvision"
        assert all(count == 1 for count in detect_counts.values())
        assert len(candidates) == 4
        assert not any(c.get("skipped") for c in candidates)

    def test_wiped_master_block_falls_through_to_carver(self, tmp_path):
        normal_dd = self.FIXTURES_DIR / "hikvision_normal.dd"
        if not normal_dd.exists():
            pytest.skip("hikvision_normal.dd not found")

        # Copy and wipe the first 0x1000 bytes (master block / signatures)
        wiped_dd = tmp_path / "wiped_hikvision.dd"
        content = bytearray(normal_dd.read_bytes())
        content[:0x1000] = b"\x00" * 0x1000
        wiped_dd.write_bytes(content)

        manager = ParserManager()
        parser, conf, info, candidates = manager.detect_candidates(str(wiped_dd), exhaustive=False)

        assert parser is not None
        assert parser.vendor_name == "generic_dvr_carver"
        assert conf == 0.65

        # Check candidate evaluation order & skipping
        generic_cand = next(c for c in candidates if c["vendor"] == "generic")
        assert generic_cand.get("skipped") == "outscored by generic_dvr_carver"

    def test_video_analyze_performs_single_detection_pass(self, tmp_path, monkeypatch):
        synthetic_dd = self.FIXTURES_DIR / "hikvision_synthetic.dd"
        if not synthetic_dd.exists():
            pytest.skip("hikvision_synthetic.dd not found")

        detect_candidate_calls = 0
        import backend.api.main as api_main
        orig_detect_candidates = api_main.parser_manager.detect_candidates

        def spy_detect_candidates(*args, **kwargs):
            nonlocal detect_candidate_calls
            detect_candidate_calls += 1
            return orig_detect_candidates(*args, **kwargs)

        monkeypatch.setattr(api_main.parser_manager, "detect_candidates", spy_detect_candidates)

        monkeypatch.setenv("ORIGINAL_EVIDENCE_ROOT", str(tmp_path / "original"))
        monkeypatch.setenv("WORKING_COPY_ROOT", str(tmp_path / "working"))
        monkeypatch.setenv("EXTRACTED_MEDIA_ROOT", str(tmp_path / "extracted"))
        get_settings.cache_clear()

        try:
            with TestClient(fastapi_app) as client:
                with open(synthetic_dd, "rb") as f:
                    res = client.post(
                        "/video/analyze",
                        files={"file": ("hikvision_synthetic.dd", f, "application/octet-stream")},
                    )
                # detect_candidates was called exactly once during the flow
                assert detect_candidate_calls == 1
        finally:
            get_settings.cache_clear()

    def test_parse_cli_on_hikvision_normal_shows_skipped_not_nomatch(self):
        normal_dd = self.FIXTURES_DIR / "hikvision_normal.dd"
        if not normal_dd.exists():
            pytest.skip("hikvision_normal.dd not found")

        runner = CliRunner()
        res = runner.invoke(cli_app, ["parse", str(normal_dd)])
        assert res.exit_code == 0
        assert "generic_dvr_carver: skipped" in res.output
        assert "generic_dvr_carver: no-match" not in res.output

    def test_precomputed_detection_mismatch_re_detects_and_logs_warning(self, tmp_path, monkeypatch, caplog):
        normal_dd = self.FIXTURES_DIR / "hikvision_normal.dd"
        synthetic_dd = self.FIXTURES_DIR / "hikvision_synthetic.dd"
        if not normal_dd.exists() or not synthetic_dd.exists():
            pytest.skip("fixtures not found")

        manager = ParserManager()
        # Precompute detection result on normal_dd
        parser_norm, conf_norm, info_norm = manager.detect(str(normal_dd))

        out_dir = tmp_path / "out"
        out_dir.mkdir()

        # Pass normal_dd's precomputed detection info while parsing synthetic_dd
        import logging
        with caplog.at_level(logging.WARNING):
            res = manager.parse(
                str(synthetic_dd),
                str(out_dir),
                detection_result=(parser_norm, conf_norm, info_norm),
            )

        # Mismatch warning logged
        assert any("Precomputed detection result does not match evidence file" in r.message for r in caplog.records)
        # Parse succeeded by re-detecting
        assert res.success is True
        assert res.detection_info["evidence_path"] == str(synthetic_dd.resolve())

    def test_cli_analyze_performs_single_detection_pass(self, monkeypatch):
        synthetic_dd = self.FIXTURES_DIR / "hikvision_synthetic.dd"
        if not synthetic_dd.exists():
            pytest.skip("hikvision_synthetic.dd not found")

        calls = 0
        orig_detect_candidates = ParserManager.detect_candidates

        def spy_detect_candidates(self, *args, **kwargs):
            nonlocal calls
            calls += 1
            return orig_detect_candidates(self, *args, **kwargs)

        monkeypatch.setattr(ParserManager, "detect_candidates", spy_detect_candidates)

        runner = CliRunner()
        res = runner.invoke(cli_app, ["analyze", str(synthetic_dd)])
        assert res.exit_code == 0
        assert calls == 1

    def test_interactive_wizard_performs_single_detection_pass(self, monkeypatch):
        import io
        from rich.console import Console
        from rich.prompt import Prompt
        from backend.cli.theme import _THEME
        import backend.cli.interactive as interactive

        synthetic_dd = self.FIXTURES_DIR / "hikvision_synthetic.dd"
        if not synthetic_dd.exists():
            pytest.skip("hikvision_synthetic.dd not found")

        calls = 0
        orig_detect_candidates = ParserManager.detect_candidates

        def spy_detect_candidates(self, *args, **kwargs):
            nonlocal calls
            calls += 1
            return orig_detect_candidates(self, *args, **kwargs)

        monkeypatch.setattr(ParserManager, "detect_candidates", spy_detect_candidates)
        monkeypatch.setattr(Prompt, "ask", lambda *args, **kwargs: str(synthetic_dd))

        console = Console(theme=_THEME, file=io.StringIO())
        interactive._run_pipeline_once(console)
        assert calls == 1

    def test_tui_engine_performs_single_detection_pass(self, monkeypatch):
        from backend.cli.tui.engine import TraceXPipelineEngine

        synthetic_dd = self.FIXTURES_DIR / "hikvision_synthetic.dd"
        if not synthetic_dd.exists():
            pytest.skip("hikvision_synthetic.dd not found")

        calls = 0
        orig_detect_candidates = ParserManager.detect_candidates

        def spy_detect_candidates(self, *args, **kwargs):
            nonlocal calls
            calls += 1
            return orig_detect_candidates(self, *args, **kwargs)

        monkeypatch.setattr(ParserManager, "detect_candidates", spy_detect_candidates)

        engine = TraceXPipelineEngine()
        res = engine.run_pipeline(str(synthetic_dd))
        assert res.vendor_name == "hikvision"
        assert calls == 1



