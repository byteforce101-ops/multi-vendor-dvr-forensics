from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.api.auth import AuthenticatedUser, get_current_user
from backend.config.settings import get_settings
from backend.core.acquisition.service import hash_evidence, import_evidence, import_uploaded_evidence, verify_evidence
from backend.db.database import get_db
from backend.db.models import Case, Evidence
from backend.db.schemas import CaseCreate, CaseRead, EvidenceCreate, EvidenceRead
from backend.db.services import persist_parse_result
from backend.parsers.registry import ParserManager

app = FastAPI(title="DVR Forensic Platform")
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)
parser_manager = ParserManager()


def _require_case_access(case: Case, user: AuthenticatedUser | None) -> None:
    """Protect case data when Supabase token verification is enabled."""
    if user and case.owner_auth_id and case.owner_auth_id != user.user_id:
        raise HTTPException(403, "You do not have access to this case")


@app.post("/cases", response_model=CaseRead, status_code=201)
def create_case(payload: CaseCreate, db: Session = Depends(get_db), user: AuthenticatedUser | None = Depends(get_current_user)):
    case = Case(**payload.model_dump(), owner_auth_id=user.user_id if user else None)
    db.add(case)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if payload.case_number:
            raise HTTPException(409, f"Case number already exists: {payload.case_number}") from exc
        raise
    db.refresh(case)
    return case


@app.get("/cases/{case_id}", response_model=CaseRead)
def get_case(case_id: str, db: Session = Depends(get_db), user: AuthenticatedUser | None = Depends(get_current_user)):
    case = db.get(Case, case_id)
    if not case:
        raise HTTPException(404, "Case not found")
    _require_case_access(case, user)
    return case


@app.post("/cases/{case_id}/evidence", response_model=EvidenceRead, status_code=201)
def add_evidence(case_id: str, payload: EvidenceCreate, db: Session = Depends(get_db), user: AuthenticatedUser | None = Depends(get_current_user)):
    case = db.get(Case, case_id)
    if not case:
        raise HTTPException(404, "Case not found")
    _require_case_access(case, user)
    try:
        evidence = hash_evidence(db, import_evidence(db, case_id, payload.source_path))
    except FileNotFoundError as exc:
        raise HTTPException(422, f"Evidence source does not exist: {exc}") from exc
    return evidence


@app.post("/cases/{case_id}/evidence/upload", response_model=EvidenceRead, status_code=201)
def upload_evidence(case_id: str, file: UploadFile = File(...), db: Session = Depends(get_db), user: AuthenticatedUser | None = Depends(get_current_user)):
    case = db.get(Case, case_id)
    if not case:
        raise HTTPException(404, "Case not found")
    _require_case_access(case, user)
    if not file.filename:
        raise HTTPException(422, "An evidence file is required")
    evidence = hash_evidence(db, import_uploaded_evidence(db, case_id, file))
    return evidence


@app.get("/cases/{case_id}/evidence", response_model=list[EvidenceRead])
def list_evidence(case_id: str, db: Session = Depends(get_db), user: AuthenticatedUser | None = Depends(get_current_user)):
    case = db.get(Case, case_id)
    if not case:
        raise HTTPException(404, "Case not found")
    _require_case_access(case, user)
    return db.query(Evidence).filter(Evidence.case_id == case_id).all()


@app.get("/evidence/{evidence_id}", response_model=EvidenceRead)
def get_evidence(evidence_id: str, db: Session = Depends(get_db), user: AuthenticatedUser | None = Depends(get_current_user)):
    evidence = db.get(Evidence, evidence_id)
    if not evidence:
        raise HTTPException(404, "Evidence not found")
    _require_case_access(evidence.case, user)
    return evidence


@app.post("/evidence/{evidence_id}/verify", response_model=EvidenceRead)
def verify(evidence_id: str, db: Session = Depends(get_db), user: AuthenticatedUser | None = Depends(get_current_user)):
    evidence = db.get(Evidence, evidence_id)
    if not evidence:
        raise HTTPException(404, "Evidence not found")
    _require_case_access(evidence.case, user)
    return verify_evidence(db, evidence)


@app.post("/evidence/{evidence_id}/parse", response_model=EvidenceRead)
def parse_evidence(evidence_id: str, db: Session = Depends(get_db), user: AuthenticatedUser | None = Depends(get_current_user)):
    evidence = db.get(Evidence, evidence_id)
    if not evidence:
        raise HTTPException(404, "Evidence not found")
    _require_case_access(evidence.case, user)
    output_dir = str(get_settings().extracted_media_root / evidence_id)
    _, _, device_info = parser_manager.detect(evidence.working_copy_path)
    result = parser_manager.parse(evidence.working_copy_path, output_dir)
    persist_parse_result(db, evidence, result, device_info)
    db.refresh(evidence)
    return evidence


@app.post("/evidence/{evidence_id}/extract", response_model=EvidenceRead)
def extract_evidence(evidence_id: str, db: Session = Depends(get_db), user: AuthenticatedUser | None = Depends(get_current_user)):
    evidence = db.get(Evidence, evidence_id)
    if not evidence:
        raise HTTPException(404, "Evidence not found")
    _require_case_access(evidence.case, user)
    output_dir = str(get_settings().extracted_media_root / evidence_id)
    parse_result = parser_manager.parse(evidence.working_copy_path, output_dir)
    if not parse_result.success:
        raise HTTPException(422, f"Parse failed before extraction: {parse_result.errors}")
    extract_result = parser_manager.extract(evidence.working_copy_path, output_dir, parse_result)
    _, _, device_info = parser_manager.detect(evidence.working_copy_path)
    persist_parse_result(db, evidence, extract_result, device_info)
    db.refresh(evidence)
    return evidence

from pydantic import BaseModel
from backend.db.models import Event
from backend.db.schemas import EventRead
from backend.db.services import persist_video_events
from backend.db.repositories.events_repository import EventsRepository
from backend.core.search.service import SearchService
from backend.video.analysis.service import VideoAnalysisService

video_analysis_service = VideoAnalysisService()


@app.post("/evidence/{evidence_id}/analyze")
def analyze_evidence(evidence_id: str, db: Session = Depends(get_db), user: AuthenticatedUser | None = Depends(get_current_user)):
    evidence = db.get(Evidence, evidence_id)
    if not evidence:
        raise HTTPException(404, "Evidence not found")
    _require_case_access(evidence.case, user)
    if not evidence.recordings:
        raise HTTPException(422, "No recordings to analyze - parse/extract evidence first")

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
        raise HTTPException(422, {"message": "No recordings could be analyzed", "errors": errors})
    return {"events": [EventRead.model_validate(e) for e in all_events], "errors": errors}


class SearchRequest(BaseModel):
    query: str


@app.post("/cases/{case_id}/search")
def search_case(case_id: str, payload: SearchRequest, db: Session = Depends(get_db), user: AuthenticatedUser | None = Depends(get_current_user)):
    case = db.get(Case, case_id)
    if not case:
        raise HTTPException(404, "Case not found")
    _require_case_access(case, user)
    service = SearchService(EventsRepository(db))
    return service.search(case_id=case_id, nl_query=payload.query)
