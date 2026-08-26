from pathlib import Path

from fastapi.testclient import TestClient

from backend.api.main import app
from backend.db.database import get_db
from backend.db.models import Base
from backend.db.database import create_session_factory


FIXTURE = Path("backend/tests/fixtures/hikvision_synthetic.dd")


def test_case_evidence_parse_and_retrieve(tmp_path, monkeypatch):
    """The API persists Hikvision ParseResult without coupling the parser to ORM."""
    database_url = f"sqlite:///{tmp_path / 'forensics.db'}"
    engine, session_factory = create_session_factory(database_url)
    Base.metadata.create_all(engine)

    def test_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    # The acquisition service reads these settings for the forensic copy boundary.
    monkeypatch.setenv("ORIGINAL_EVIDENCE_ROOT", str(tmp_path / "original"))
    monkeypatch.setenv("WORKING_COPY_ROOT", str(tmp_path / "working"))
    monkeypatch.setenv("EXTRACTED_MEDIA_ROOT", str(tmp_path / "extracted"))
    from backend.config.settings import get_settings
    get_settings.cache_clear()
    app.dependency_overrides[get_db] = test_db

    try:
        with TestClient(app) as client:
            case_response = client.post("/cases", json={"name": "Demo", "investigator": "Examiner"})
            assert case_response.status_code == 201
            case_id = case_response.json()["id"]

            evidence_response = client.post(
                f"/cases/{case_id}/evidence", json={"source_path": str(FIXTURE.resolve())}
            )
            assert evidence_response.status_code == 201
            evidence_id = evidence_response.json()["id"]
            assert evidence_response.json()["sha256"]

            parse_response = client.post(f"/evidence/{evidence_id}/parse")
            assert parse_response.status_code == 200
            parsed = parse_response.json()
            assert parsed["vendor"] == "hikvision"
            assert len(parsed["devices"]) == 1
            assert len(parsed["recordings"]) == 3

            fetched = client.get(f"/evidence/{evidence_id}")
            assert fetched.status_code == 200
            assert len(fetched.json()["recordings"]) == 3
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()
