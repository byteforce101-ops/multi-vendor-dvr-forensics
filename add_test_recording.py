from datetime import datetime, timezone
from backend.db.database import SessionLocal
from backend.db.models import Recording

db = SessionLocal()

recording = Recording(
    evidence_id="dd6081c7-84fe-41a7-a740-31dcc591aa13",
    device_id=None,
    camera_id="CH-TEST",
    recording_identifier="manual-test-mp4",
    source_path=r"C:\Users\sarthak\Downloads\WhatsApp Video 2026-08-18 at 7.29.43 PM.mp4",
    extracted_path=None,
    original_timestamp=datetime(2026, 8, 18, 19, 29, 43, tzinfo=timezone.utc),
    normalized_timestamp=datetime(2026, 8, 18, 19, 29, 43, tzinfo=timezone.utc),
    recovery_status="RECOVERED",
    raw_metadata={"source": "manual test insert, not from parser"},
)
db.add(recording)
db.commit()
print("Created recording:", recording.id)
db.close()