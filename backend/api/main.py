from datetime import datetime, timezone
from pathlib import Path
import shutil
import uuid

from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
    UploadFile,
    File,
)

from sqlalchemy.orm import Session

from backend.api.auth import (
    AuthenticatedUser,
    get_current_user,
)

from backend.config.settings import get_settings

from backend.core.acquisition.service import (
    hash_evidence,
    import_evidence,
    verify_evidence,
)

from backend.db.database import get_db

from backend.db.models import (
    Case,
    Evidence,
)

from backend.db.schemas import (
    CaseCreate,
    CaseRead,
    EvidenceCreate,
    EvidenceRead,
)

from backend.db.services import (
    persist_parse_result,
)

from backend.parsers.registry import (
    ParserManager,
)

from backend.video.analysis.service import (
    VideoAnalysisService,
)


# =========================================================
# APPLICATION
# =========================================================

app = FastAPI(
    title="DVR Forensic Platform"
)


# =========================================================
# SERVICES
# =========================================================

parser_manager = ParserManager()

video_analysis_service = VideoAnalysisService(
    yolo_model="yolo26n.pt",
    ai_confidence=0.35,
    ai_iou=0.50,
)


# =========================================================
# CASE ACCESS
# =========================================================

def _require_case_access(
    case: Case,
    user: AuthenticatedUser | None,
) -> None:

    """
    Protect case data when Supabase token
    verification is enabled.
    """

    if (
        user
        and case.owner_auth_id
        and case.owner_auth_id != user.user_id
    ):
        raise HTTPException(
            status_code=403,
            detail="You do not have access to this case",
        )


# =========================================================
# CASES
# =========================================================

@app.post(
    "/cases",
    response_model=CaseRead,
    status_code=201,
)
def create_case(
    payload: CaseCreate,
    db: Session = Depends(get_db),
    user: AuthenticatedUser | None = Depends(
        get_current_user
    ),
):

    case = Case(
        **payload.model_dump(),
        owner_auth_id=(
            user.user_id
            if user
            else None
        ),
    )

    db.add(case)
    db.commit()
    db.refresh(case)

    return case


@app.get(
    "/cases/{case_id}",
    response_model=CaseRead,
)
def get_case(
    case_id: str,
    db: Session = Depends(get_db),
    user: AuthenticatedUser | None = Depends(
        get_current_user
    ),
):

    case = db.get(
        Case,
        case_id,
    )

    if not case:
        raise HTTPException(
            status_code=404,
            detail="Case not found",
        )

    _require_case_access(
        case,
        user,
    )

    return case


# =========================================================
# EVIDENCE
# =========================================================

@app.post(
    "/cases/{case_id}/evidence",
    response_model=EvidenceRead,
    status_code=201,
)
def add_evidence(
    case_id: str,
    payload: EvidenceCreate,
    db: Session = Depends(get_db),
    user: AuthenticatedUser | None = Depends(
        get_current_user
    ),
):

    case = db.get(
        Case,
        case_id,
    )

    if not case:
        raise HTTPException(
            status_code=404,
            detail="Case not found",
        )

    _require_case_access(
        case,
        user,
    )

    try:

        evidence = hash_evidence(
            db,
            import_evidence(
                db,
                case_id,
                payload.source_path,
            ),
        )

    except FileNotFoundError as exc:

        raise HTTPException(
            status_code=422,
            detail=(
                f"Evidence source does not exist: {exc}"
            ),
        ) from exc

    return evidence


@app.get(
    "/cases/{case_id}/evidence",
    response_model=list[EvidenceRead],
)
def list_evidence(
    case_id: str,
    db: Session = Depends(get_db),
    user: AuthenticatedUser | None = Depends(
        get_current_user
    ),
):

    case = db.get(
        Case,
        case_id,
    )

    if not case:
        raise HTTPException(
            status_code=404,
            detail="Case not found",
        )

    _require_case_access(
        case,
        user,
    )

    return (
        db.query(Evidence)
        .filter(
            Evidence.case_id == case_id
        )
        .all()
    )


@app.get(
    "/evidence/{evidence_id}",
    response_model=EvidenceRead,
)
def get_evidence(
    evidence_id: str,
    db: Session = Depends(get_db),
    user: AuthenticatedUser | None = Depends(
        get_current_user
    ),
):

    evidence = db.get(
        Evidence,
        evidence_id,
    )

    if not evidence:
        raise HTTPException(
            status_code=404,
            detail="Evidence not found",
        )

    _require_case_access(
        evidence.case,
        user,
    )

    return evidence


@app.post(
    "/evidence/{evidence_id}/verify",
    response_model=EvidenceRead,
)
def verify(
    evidence_id: str,
    db: Session = Depends(get_db),
    user: AuthenticatedUser | None = Depends(
        get_current_user
    ),
):

    evidence = db.get(
        Evidence,
        evidence_id,
    )

    if not evidence:
        raise HTTPException(
            status_code=404,
            detail="Evidence not found",
        )

    _require_case_access(
        evidence.case,
        user,
    )

    return verify_evidence(
        db,
        evidence,
    )


# =========================================================
# PARSING
# =========================================================

@app.post(
    "/evidence/{evidence_id}/parse",
    response_model=EvidenceRead,
)
def parse_evidence(
    evidence_id: str,
    db: Session = Depends(get_db),
    user: AuthenticatedUser | None = Depends(
        get_current_user
    ),
):

    evidence = db.get(
        Evidence,
        evidence_id,
    )

    if not evidence:
        raise HTTPException(
            status_code=404,
            detail="Evidence not found",
        )

    _require_case_access(
        evidence.case,
        user,
    )

    output_dir = str(
        get_settings().extracted_media_root
        / evidence_id
    )

    _, _, device_info = parser_manager.detect(
        evidence.working_copy_path
    )

    result = parser_manager.parse(
        evidence.working_copy_path,
        output_dir,
    )

    persist_parse_result(
        db,
        evidence,
        result,
        device_info,
    )

    db.refresh(evidence)

    return evidence


# =========================================================
# EXTRACTION
# =========================================================

@app.post(
    "/evidence/{evidence_id}/extract",
    response_model=EvidenceRead,
)
def extract_evidence(
    evidence_id: str,
    db: Session = Depends(get_db),
    user: AuthenticatedUser | None = Depends(
        get_current_user
    ),
):

    evidence = db.get(
        Evidence,
        evidence_id,
    )

    if not evidence:
        raise HTTPException(
            status_code=404,
            detail="Evidence not found",
        )

    _require_case_access(
        evidence.case,
        user,
    )

    output_dir = str(
        get_settings().extracted_media_root
        / evidence_id
    )

    parse_result = parser_manager.parse(
        evidence.working_copy_path,
        output_dir,
    )

    if not parse_result.success:

        raise HTTPException(
            status_code=422,
            detail=(
                "Parse failed before extraction: "
                f"{parse_result.errors}"
            ),
        )

    extract_result = parser_manager.extract(
        evidence.working_copy_path,
        output_dir,
        parse_result,
    )

    _, _, device_info = parser_manager.detect(
        evidence.working_copy_path
    )

    persist_parse_result(
        db,
        evidence,
        extract_result,
        device_info,
    )

    db.refresh(evidence)

    return evidence

<<<<<<< HEAD
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
=======

# =========================================================
# AI VIDEO ANALYSIS
# =========================================================

@app.post(
    "/video/analyze",
)
async def analyze_video(
    file: UploadFile = File(...),
):

    """
    Upload a video and perform AI-based
    forensic video analysis.

    Pipeline:

        Upload
          ↓
        Video Probe
          ↓
        Frame Extraction
          ↓
        Motion Detection
          ↓
        YOLO Detection
          ↓
        Timestamp Conversion
          ↓
        Event Generation
          ↓
        Timeline
    """

    # -----------------------------------------------------
    # Validate filename
    # -----------------------------------------------------

    if not file.filename:

        raise HTTPException(
            status_code=400,
            detail="No filename supplied",
        )

    # -----------------------------------------------------
    # Validate extension
    # -----------------------------------------------------

    allowed_extensions = {
        ".mp4",
        ".avi",
        ".mkv",
        ".mov",
        ".wmv",
        ".ts",
        ".m4v",
    }

    extension = Path(
        file.filename
    ).suffix.lower()

    if extension not in allowed_extensions:

        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported video format: {extension}"
            ),
        )

    # -----------------------------------------------------
    # Create unique analysis ID
    # -----------------------------------------------------

    analysis_id = str(
        uuid.uuid4()
    )

    # -----------------------------------------------------
    # Create working directory
    # -----------------------------------------------------

    upload_directory = (
        Path("backend")
        / "storage"
        / "video_analysis"
        / analysis_id
    )

    upload_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    # -----------------------------------------------------
    # Working video path
    # -----------------------------------------------------

    video_path = (
        upload_directory
        / f"original{extension}"
    )

    # -----------------------------------------------------
    # Save uploaded video
    # -----------------------------------------------------

    try:

        with open(
            video_path,
            "wb",
        ) as buffer:

            shutil.copyfileobj(
                file.file,
                buffer,
            )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                f"Failed to save uploaded video: {exc}"
            ),
        ) from exc

    finally:

        await file.close()

    # -----------------------------------------------------
    # Run AI video analysis
    # -----------------------------------------------------

    try:

        result = video_analysis_service.analyze(
            video_id=analysis_id,
            camera_id="camera_01",
            video_path=video_path,

            # TEMPORARY DEVELOPMENT VALUE
            #
            # Production implementation should
            # obtain this from the DVR/NVR parser.
            video_start_time=datetime.now(
                timezone.utc
            ),

            frame_sample_fps=5.0,
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                f"Video analysis failed: {exc}"
            ),
        ) from exc

    # -----------------------------------------------------
    # Convert events to JSON
    # -----------------------------------------------------

    events = []

    for event in result.events:

        events.append(
            {
                "event_type": event.event_type,

                "video_id": event.video_id,

                "camera_id": event.camera_id,

                "start_time": (
                    event.start_time.isoformat()
                ),

                "end_time": (
                    event.end_time.isoformat()
                ),

                "confidence": event.confidence,

                "track_id": event.track_id,

                "object_type": event.object_type,

                "metadata": event.metadata,
            }
        )

    # -----------------------------------------------------
    # Convert timeline to JSON
    # -----------------------------------------------------

    timeline = []

    for item in result.timeline:

        timeline.append(
            {
                "timestamp": (
                    item.timestamp.isoformat()
                ),

                "end_timestamp": (
                    item.end_timestamp.isoformat()
                ),

                "camera_id": item.camera_id,

                "event_type": item.event_type,

                "video_id": item.video_id,

                "confidence": item.confidence,

                "object_type": item.object_type,

                "track_id": item.track_id,
            }
        )

    # -----------------------------------------------------
    # Return result
    # -----------------------------------------------------

    return {

        "status": "success",

        "analysis_id": analysis_id,

        "filename": file.filename,

        "video_path": str(
            video_path
        ),

        "metadata": {

            "duration_seconds": (
                result.metadata.duration_seconds
            ),

            "width": (
                result.metadata.width
            ),

            "height": (
                result.metadata.height
            ),

            "fps": (
                result.metadata.fps
            ),

            "codec": (
                result.metadata.codec
            ),

            "format": (
                result.metadata.format_name
            ),

            "pixel_format": (
                result.metadata.pixel_format
            ),

            "frame_count": (
                result.metadata.frame_count
            ),

            "has_audio": (
                result.metadata.has_audio
            ),
        },

        "frames_analyzed": (
            result.frame_count_analyzed
        ),

        "event_count": (
            len(events)
        ),

        "events": events,

        "timeline_count": (
            len(timeline)
        ),

        "timeline": timeline,
    }
>>>>>>> 905f04ca105dd3d99ea7785585c8d3ab1d005b7a
