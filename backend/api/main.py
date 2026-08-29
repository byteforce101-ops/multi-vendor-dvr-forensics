"""FastAPI app for the DVR Forensics Platform.

Additions in this pass (frontend integration):
  - CORS middleware (was missing entirely — the browser could not have
    called this API before now, regardless of what the frontend did).
  - GET /cases                         list cases (scoped to the caller
                                        when Supabase auth is enabled).
  - POST /cases/{case_id}/evidence/upload
                                        real multipart browser upload,
                                        using the existing
                                        import_uploaded_evidence() helper
                                        that was already written but never
                                        wired to a route.
  - GET /cases/{case_id}/events        flat event list for a case, for the
                                        frontend timeline view.

Everything else (parse/extract/analyze/search/video-analyze) is unchanged
from the existing implementation.
"""

from datetime import datetime, timezone
from pathlib import Path
import shutil
import uuid

from fastapi import Depends, FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.api.auth import AuthenticatedUser, get_current_user
from backend.config.settings import get_settings
from backend.core.acquisition.service import (
    hash_evidence,
    import_evidence,
    import_uploaded_evidence,
    verify_evidence,
)

from backend.db.database import get_db
from backend.db.models import Case, Evidence, Event
from backend.db.repositories.events_repository import EventsRepository
from backend.db.schemas import CaseCreate, CaseRead, EvidenceCreate, EvidenceRead, EventRead
from backend.db.services import persist_parse_result, persist_video_events
from backend.parsers.registry import ParserManager
from backend.video.analysis.service import VideoAnalysisService

# =========================================================
# APPLICATION
# =========================================================

app = FastAPI(title="DVR Forensic Platform")

_settings = get_settings()

app.add_middleware(
    CORSMiddleware,
    allow_origins=_settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

parser_manager = ParserManager()
video_analysis_service = VideoAnalysisService(
    yolo_model="yolo26n.pt",
    ai_confidence=0.35,
    ai_iou=0.50,
)


# =========================================================
# CASE ACCESS
# =========================================================

def _require_case_access(case: Case, user: AuthenticatedUser | None) -> None:
    """Protect case data when Supabase token verification is enabled."""
    if user and case.owner_auth_id and case.owner_auth_id != user.user_id:
        raise HTTPException(status_code=403, detail="You do not have access to this case")


# =========================================================
# CASES
# =========================================================

@app.get("/cases", response_model=list[CaseRead])
def list_cases(
    db: Session = Depends(get_db),
    user: AuthenticatedUser | None = Depends(get_current_user),
):
    query = db.query(Case)
    if user is not None:
        query = query.filter(Case.owner_auth_id == user.user_id)
    return query.order_by(Case.created_at.desc()).all()


@app.post("/cases", response_model=CaseRead, status_code=201)
def create_case(
    payload: CaseCreate,
    db: Session = Depends(get_db),
    user: AuthenticatedUser | None = Depends(get_current_user),
):
    case = Case(**payload.model_dump(), owner_auth_id=user.user_id if user else None)
    db.add(case)
    db.commit()
    db.refresh(case)
    return case


@app.get("/cases/{case_id}", response_model=CaseRead)
def get_case(
    case_id: str,
    db: Session = Depends(get_db),
    user: AuthenticatedUser | None = Depends(get_current_user),
):
    case = db.get(Case, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    _require_case_access(case, user)
    return case


# =========================================================
# EVIDENCE
# =========================================================

@app.post("/cases/{case_id}/evidence", response_model=EvidenceRead, status_code=201)
def add_evidence(
    case_id: str,
    payload: EvidenceCreate,
    db: Session = Depends(get_db),
    user: AuthenticatedUser | None = Depends(get_current_user),
):
    """Register evidence that already lives on the server's filesystem
    (used by the CLI / server-side scripts). Browser uploads should use
    POST /cases/{case_id}/evidence/upload instead."""
    case = db.get(Case, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    _require_case_access(case, user)
    try:
        evidence = hash_evidence(db, import_evidence(db, case_id, payload.source_path))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=422, detail=f"Evidence source does not exist: {exc}") from exc
    return evidence


@app.post("/cases/{case_id}/evidence/upload", response_model=EvidenceRead, status_code=201)
async def upload_evidence(
    case_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: AuthenticatedUser | None = Depends(get_current_user),
):
    """Browser-facing upload: accepts the raw file, stages it, copies it
    through the same acquisition boundary the CLI uses (immutable original +
    disposable working copy), then hashes it."""
    case = db.get(Case, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    _require_case_access(case, user)
    try:
        evidence = hash_evidence(db, import_uploaded_evidence(db, case_id, file))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=422, detail=f"Upload failed: {exc}") from exc
    return evidence


@app.get("/cases/{case_id}/evidence", response_model=list[EvidenceRead])
def list_evidence(
    case_id: str,
    db: Session = Depends(get_db),
    user: AuthenticatedUser | None = Depends(get_current_user),
):
    case = db.get(Case, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    _require_case_access(case, user)
    return db.query(Evidence).filter(Evidence.case_id == case_id).all()


@app.get("/evidence/{evidence_id}", response_model=EvidenceRead)
def get_evidence(
    evidence_id: str,
    db: Session = Depends(get_db),
    user: AuthenticatedUser | None = Depends(get_current_user),
):
    evidence = db.get(Evidence, evidence_id)
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence not found")
    _require_case_access(evidence.case, user)
    return evidence


@app.post("/evidence/{evidence_id}/verify", response_model=EvidenceRead)
def verify(
    evidence_id: str,
    db: Session = Depends(get_db),
    user: AuthenticatedUser | None = Depends(get_current_user),
):
    evidence = db.get(Evidence, evidence_id)
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence not found")
    _require_case_access(evidence.case, user)
    return verify_evidence(db, evidence)


# =========================================================
# PARSING / EXTRACTION
# =========================================================

@app.post("/evidence/{evidence_id}/parse", response_model=EvidenceRead)
def parse_evidence(
    evidence_id: str,
    db: Session = Depends(get_db),
    user: AuthenticatedUser | None = Depends(get_current_user),
):
    evidence = db.get(Evidence, evidence_id)
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence not found")
    _require_case_access(evidence.case, user)

    output_dir = str(get_settings().extracted_media_root / evidence_id)
    _, _, device_info = parser_manager.detect(evidence.working_copy_path)
    result = parser_manager.parse(evidence.working_copy_path, output_dir)
    persist_parse_result(db, evidence, result, device_info)
    db.refresh(evidence)
    return evidence


@app.post("/evidence/{evidence_id}/extract", response_model=EvidenceRead)
def extract_evidence(
    evidence_id: str,
    db: Session = Depends(get_db),
    user: AuthenticatedUser | None = Depends(get_current_user),
):
    evidence = db.get(Evidence, evidence_id)
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence not found")
    _require_case_access(evidence.case, user)

    output_dir = str(get_settings().extracted_media_root / evidence_id)
    parse_result = parser_manager.parse(evidence.working_copy_path, output_dir)
    if not parse_result.success:
        raise HTTPException(status_code=422, detail=f"Parse failed before extraction: {parse_result.errors}")

    extract_result = parser_manager.extract(evidence.working_copy_path, output_dir, parse_result)
    _, _, device_info = parser_manager.detect(evidence.working_copy_path)
    persist_parse_result(db, evidence, extract_result, device_info)
    db.refresh(evidence)
    return evidence


# =========================================================
# ANALYSIS
# =========================================================

@app.post("/evidence/{evidence_id}/analyze")
def analyze_evidence(
    evidence_id: str,
    db: Session = Depends(get_db),
    user: AuthenticatedUser | None = Depends(get_current_user),
):
    evidence = db.get(Evidence, evidence_id)
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence not found")
    _require_case_access(evidence.case, user)
    if not evidence.recordings:
        raise HTTPException(status_code=422, detail="No recordings to analyze - parse/extract evidence first")

    all_events = []
    errors = []
    for recording in evidence.recordings:
        if not (recording.normalized_timestamp or recording.original_timestamp):
            errors.append({"recording_id": recording.id, "error": "no timestamp available"})
            continue
        try:
            result = video_analysis_service.analyze(
                video_id=recording.id,
                camera_id=recording.camera_id,
                video_path=recording.extracted_path or recording.source_path,
                video_start_time=recording.normalized_timestamp or recording.original_timestamp,
            )
            all_events += persist_video_events(db, evidence, recording, result.events)
        except Exception as exc:
            errors.append({"recording_id": recording.id, "error": str(exc)})

    if errors and not all_events:
        raise HTTPException(status_code=422, detail={"message": "No recordings could be analyzed", "errors": errors})

    return {"events": [EventRead.model_validate(e) for e in all_events], "errors": errors}


@app.get("/cases/{case_id}/events", response_model=list[EventRead])
def list_case_events(
    case_id: str,
    db: Session = Depends(get_db),
    user: AuthenticatedUser | None = Depends(get_current_user),
):
    case = db.get(Case, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    _require_case_access(case, user)
    return db.query(Event).filter(Event.case_id == case_id).order_by(Event.start_time).all()


# =========================================================
# SEARCH
# =========================================================

class SearchRequest(BaseModel):
    query: str



@app.post("/cases/{case_id}/search")
def search_case(
    case_id: str,
    payload: SearchRequest,
    db: Session = Depends(get_db),
    user: AuthenticatedUser | None = Depends(get_current_user),
):
    case = db.get(Case, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    _require_case_access(case, user)

    try:
        from backend.core.search.service import SearchService
    except ImportError as exc:
        raise HTTPException(status_code=503, detail=f"Search requires the 'groq' package: {exc}") from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Search is unavailable: {exc}") from exc

    service = SearchService(EventsRepository(db))
    return service.search(case_id=case_id, nl_query=payload.query)


# =========================================================
# STANDALONE AI VIDEO ANALYSIS (no case/evidence attached)
# =========================================================

@app.post("/video/analyze")
async def analyze_video(file: UploadFile = File(...)):
    """Upload a video and run the AI pipeline without a case/evidence
    record. Kept for ad-hoc analysis; the case-integrated flow above
    (/evidence/{id}/analyze) is what the main UI uses."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename supplied")

    allowed_extensions = {".mp4", ".avi", ".mkv", ".mov", ".wmv", ".ts", ".m4v"}
    extension = Path(file.filename).suffix.lower()
    if extension not in allowed_extensions:
        raise HTTPException(status_code=400, detail=f"Unsupported video format: {extension}")

    analysis_id = str(uuid.uuid4())
    upload_directory = Path("backend") / "storage" / "video_analysis" / analysis_id
    upload_directory.mkdir(parents=True, exist_ok=True)
    video_path = upload_directory / f"original{extension}"

    try:
        with open(video_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to save uploaded video: {exc}") from exc
    finally:
        await file.close()

    try:
        result = video_analysis_service.analyze(
            video_id=analysis_id,
            camera_id="camera_01",
            video_path=video_path,
            video_start_time=datetime.now(timezone.utc),
            frame_sample_fps=5.0,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Video analysis failed: {exc}") from exc

    events = [
        {
            "event_type": e.event_type,
            "video_id": e.video_id,
            "camera_id": e.camera_id,
            "start_time": e.start_time.isoformat(),
            "end_time": e.end_time.isoformat(),
            "confidence": e.confidence,
            "track_id": e.track_id,
            "object_type": e.object_type,
            "metadata": e.metadata,
        }
        for e in result.events
    ]

    return {
        "status": "success",
        "analysis_id": analysis_id,
        "filename": file.filename,
        "metadata": {
            "duration_seconds": result.metadata.duration_seconds,
            "width": result.metadata.width,
            "height": result.metadata.height,
            "fps": result.metadata.fps,
            "codec": result.metadata.codec,
        },
        "frames_analyzed": result.frame_count_analyzed,
        "event_count": len(events),
        "events": events,
    }