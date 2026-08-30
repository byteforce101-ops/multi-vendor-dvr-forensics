"""FastAPI app for the DVR Forensics Platform."""

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
from backend.db.schemas import (
    CaseCreate,
    CaseRead,
    EvidenceCreate,
    EvidenceRead,
    EventRead,
)
from backend.db.services import (
    persist_parse_result,
    persist_video_events,
)

from backend.parsers.registry import ParserManager
from backend.video.analysis.service import VideoAnalysisService
from backend.cli.interactive import _run_video_integrity_analysis

# =========================================================
# APPLICATION
# =========================================================

app = FastAPI(
    title="DVR Forensic Platform"
)

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


def _build_integrity_response(video_path: Path) -> dict:
    """Expose the same video integrity checks used by the CLI."""
    try:
        integrity = _run_video_integrity_analysis(video_path)
    except Exception as exc:
        return {
            "available": False,
            "error": str(exc),
            "timestamp_continuity": False,
            "frame_continuity": False,
            "fps_consistency": False,
            "duplicate_frames": False,
            "metadata_consistency": False,
            "resolution_consistency": False,
            "compression_consistency": False,
            "frames_checked": 0,
            "timestamp_gaps": 0,
            "duplicate_sequences": 0,
            "corrupted_frames": 0,
            "fps_changes": 0,
            "resolution_changes": 0,
            "compression_changes": 0,
            "details": {},
            "anomalies": [f"Integrity analysis could not be completed: {exc}"],
            "integrity_score": 0.0,
            "overall_status": "ERROR",
        }

    checks = [
        integrity.get("timestamp_continuity", False),
        integrity.get("frame_continuity", False),
        integrity.get("fps_consistency", False),
        integrity.get("duplicate_frames", False),
        integrity.get("metadata_consistency", False),
        integrity.get("resolution_consistency", False),
        integrity.get("compression_consistency", False),
    ]

    score = round(
        (sum(bool(value) for value in checks) / len(checks)) * 100,
        1,
    )

    anomalies = list(integrity.get("anomalies", []))

    return {
        "available": True,
        "timestamp_continuity": bool(integrity.get("timestamp_continuity", False)),
        "frame_continuity": bool(integrity.get("frame_continuity", False)),
        "fps_consistency": bool(integrity.get("fps_consistency", False)),
        "duplicate_frames": bool(integrity.get("duplicate_frames", False)),
        "metadata_consistency": bool(integrity.get("metadata_consistency", False)),
        "resolution_consistency": bool(integrity.get("resolution_consistency", False)),
        "compression_consistency": bool(integrity.get("compression_consistency", False)),
        "frames_checked": int(integrity.get("frames_checked", 0)),
        "timestamp_gaps": int(integrity.get("timestamp_gaps", 0)),
        "duplicate_sequences": int(integrity.get("duplicate_sequences", 0)),
        "corrupted_frames": int(integrity.get("corrupted_frames", 0)),
        "fps_changes": int(integrity.get("fps_changes", 0)),
        "resolution_changes": int(integrity.get("resolution_changes", 0)),
        "compression_changes": int(integrity.get("compression_changes", 0)),
        "details": integrity.get("details", {}),
        "anomalies": anomalies,
        "integrity_score": score,
        "overall_status": "WARNING" if anomalies else "PASS",
    }


def _build_object_disappearance_response(events: list) -> dict:
    """Mirror the CLI's repeated-object disappearance heuristic."""
    from datetime import timedelta

    observations = {}

    for event in events:
        object_type = getattr(event, "object_type", None)
        if not object_type:
            continue

        object_type = str(object_type).strip().lower()

        if object_type in {"motion", "unknown", "none", ""}:
            continue

        start_time = getattr(event, "start_time", None)
        end_time = getattr(event, "end_time", None) or start_time

        if start_time is None:
            continue

        camera_id = str(
            getattr(event, "camera_id", None) or "CH-UNKNOWN"
        )

        observations.setdefault(
            (camera_id, object_type),
            [],
        ).append(
            {
                "start": start_time,
                "end": end_time,
            }
        )

    candidates = []

    for (camera_id, object_type), items in observations.items():
        items.sort(key=lambda item: item["start"])

        if len(items) < 2:
            continue

        gaps = []

        for previous, current in zip(items, items[1:]):
            try:
                gap = (
                    current["start"] - previous["end"]
                ).total_seconds()

                if gap >= 0:
                    gaps.append(gap)
            except Exception:
                pass

        median_gap = 1.0

        if gaps:
            ordered = sorted(gaps)
            median_gap = ordered[len(ordered) // 2]

        disappearance_delay = max(
            2.0,
            median_gap * 3.0,
        )

        last_seen = max(
            item["end"]
            for item in items
        )

        disappearance_time = (
            last_seen
            + timedelta(seconds=disappearance_delay)
        )

        candidates.append(
            {
                "camera_id": camera_id,
                "object_type": object_type,
                "first_seen": items[0]["start"].isoformat(),
                "last_seen": last_seen.isoformat(),
                "disappearance_time": disappearance_time.isoformat(),
                "observation_count": len(items),
                "related_activity": [],
            }
        )

    for candidate in candidates:
        try:
            disappearance_time = datetime.fromisoformat(
                candidate["disappearance_time"]
            )
        except Exception:
            continue

        for event in events:
            event_camera = str(
                getattr(event, "camera_id", None)
                or "CH-UNKNOWN"
            )

            if event_camera != candidate["camera_id"]:
                continue

            event_start = getattr(event, "start_time", None)

            if event_start is None or event_start < disappearance_time:
                continue

            event_type = getattr(
                event,
                "event_type",
                "activity",
            )
            event_object = getattr(
                event,
                "object_type",
                None,
            )

            text = (
                f"{event_start.isoformat()} → {event_type}"
            )

            if event_object:
                text += f" ({event_object})"

            candidate["related_activity"].append(text)

            if len(candidate["related_activity"]) >= 3:
                break

    return {
        "available": True,
        "count": len(candidates),
        "disappearances": candidates,
        "note": (
            "Object disappearance is a forensic observation. "
            "It does not prove that the object was removed, stolen, "
            "hidden, or that the footage was manipulated."
        ),
    }


# =========================================================
# CASE ACCESS
# =========================================================

def _require_case_access(
    case: Case,
    user: AuthenticatedUser | None,
) -> None:

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

@app.get(
    "/cases",
    response_model=list[CaseRead],
)
def list_cases(
    db: Session = Depends(get_db),
    user: AuthenticatedUser | None = Depends(
        get_current_user
    ),
):

    query = db.query(Case)

    if user is not None:
        query = query.filter(
            Case.owner_auth_id == user.user_id
        )

    return query.order_by(
        Case.created_at.desc()
    ).all()


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


@app.post(
    "/cases/{case_id}/evidence/upload",
    response_model=EvidenceRead,
    status_code=201,
)
async def upload_evidence(
    case_id: str,
    file: UploadFile = File(...),
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
            import_uploaded_evidence(
                db,
                case_id,
                file,
            ),
        )

    except FileNotFoundError as exc:

        raise HTTPException(
            status_code=422,
            detail=f"Upload failed: {exc}",
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
# PARSING / EXTRACTION
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


# =========================================================
# CASE-BASED ANALYSIS
# =========================================================

@app.post(
    "/evidence/{evidence_id}/analyze"
)
def analyze_evidence(
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

    if not evidence.recordings:

        raise HTTPException(
            status_code=422,
            detail=(
                "No recordings to analyze - "
                "parse/extract evidence first"
            ),
        )

    all_events = []
    errors = []

    for recording in evidence.recordings:

        if not (
            recording.normalized_timestamp
            or recording.original_timestamp
        ):

            errors.append(
                {
                    "recording_id": recording.id,
                    "error": "no timestamp available",
                }
            )

            continue

        try:

            result = (
                video_analysis_service.analyze(
                    video_id=recording.id,
                    camera_id=recording.camera_id,
                    video_path=(
                        recording.extracted_path
                        or recording.source_path
                    ),
                    video_start_time=(
                        recording.normalized_timestamp
                        or recording.original_timestamp
                    ),
                )
            )

            all_events += persist_video_events(
                db,
                evidence,
                recording,
                result.events,
            )

        except Exception as exc:

            errors.append(
                {
                    "recording_id": recording.id,
                    "error": str(exc),
                }
            )

    if errors and not all_events:

        raise HTTPException(
            status_code=422,
            detail={
                "message": (
                    "No recordings could be analyzed"
                ),
                "errors": errors,
            },
        )

    return {
        "events": [
            EventRead.model_validate(event)
            for event in all_events
        ],
        "errors": errors,
    }


@app.get(
    "/cases/{case_id}/events",
    response_model=list[EventRead],
)
def list_case_events(
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
        db.query(Event)
        .filter(
            Event.case_id == case_id
        )
        .order_by(
            Event.start_time
        )
        .all()
    )


# =========================================================
# SEARCH
# =========================================================

class SearchRequest(BaseModel):

    query: str


@app.post(
    "/cases/{case_id}/search"
)
def search_case(
    case_id: str,
    payload: SearchRequest,
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

        from backend.core.search.service import (
            SearchService,
        )

    except ImportError as exc:

        raise HTTPException(
            status_code=503,
            detail=(
                "Search requires the 'groq' package: "
                f"{exc}"
            ),
        ) from exc

    except Exception as exc:

        raise HTTPException(
            status_code=503,
            detail=(
                f"Search is unavailable: {exc}"
            ),
        ) from exc

    service = SearchService(
        EventsRepository(db)
    )

    return service.search(
        case_id=case_id,
        nl_query=payload.query,
    )


# =========================================================
# STANDALONE AI VIDEO ANALYSIS
# =========================================================

@app.post(
    "/video/analyze"
)
async def analyze_video(
    file: UploadFile = File(...),
    user: AuthenticatedUser | None = Depends(
        get_current_user
    ),
):

    """
    Upload a video and run the complete AI forensic
    analysis pipeline.

    This endpoint returns:

        - low-level AI events
        - AI forensic reconstruction
        - final forensic summary
        - video metadata
    """

    if not file.filename:

        raise HTTPException(
            status_code=400,
            detail="No filename supplied",
        )

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
                f"Unsupported video format: "
                f"{extension}"
            ),
        )

    analysis_id = str(
        uuid.uuid4()
    )

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

    video_path = (
        upload_directory
        / f"original{extension}"
    )

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
                "Failed to save uploaded video: "
                f"{exc}"
            ),
        ) from exc

    finally:

        await file.close()

    try:

        result = (
            video_analysis_service.analyze(
                video_id=analysis_id,
                camera_id="camera_01",
                video_path=video_path,
                video_start_time=datetime.now(
                    timezone.utc
                ),
                frame_sample_fps=5.0,
            )
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "Video analysis failed: "
                f"{exc}"
            ),
        ) from exc

    # =====================================================
    # LOW-LEVEL EVENTS
    # =====================================================

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

    # =====================================================
    # AI FORENSIC EVENT RECONSTRUCTION
    # =====================================================

    reconstructed_events = []

    for event in (
        result.reconstructed_events
    ):

        reconstructed_events.append(
            {
                "video_id": event.video_id,
                "camera_id": event.camera_id,
                "event_type": event.event_type,
                "start_time": (
                    event.start_time.isoformat()
                ),
                "end_time": (
                    event.end_time.isoformat()
                ),
                "title": event.title,
                "description": event.description,
                "objects": event.objects,
                "confidence": event.confidence,
                "metadata": event.metadata,
            }
        )

    # =====================================================
    # FINAL FORENSIC SUMMARY
    # =====================================================

    summary = result.forensic_summary

    forensic_summary = {

        "video_id": summary.video_id,

        "camera_id": summary.camera_id,

        "start_time": (
            summary.start_time.isoformat()
            if summary.start_time
            else None
        ),

        "end_time": (
            summary.end_time.isoformat()
            if summary.end_time
            else None
        ),

        "headline": summary.headline,

        "summary": summary.summary,

        "key_events": summary.key_events,

        "objects_detected": (
            summary.objects_detected
        ),

        "event_count": summary.event_count,

        "confidence": summary.confidence,

        "metadata": summary.metadata,
    }

    # =====================================================
    # VIDEO INTEGRITY / TAMPERING ANALYSIS
    # =====================================================

    integrity_analysis = _build_integrity_response(video_path)

    # =====================================================
    # OBJECT DISAPPEARANCE DETECTION
    # =====================================================

    object_disappearance_analysis = (
        _build_object_disappearance_response(
            result.events
        )
    )

    # =====================================================
    # COMPLETE RESPONSE
    # =====================================================

    return {

        "status": "success",

        "analysis_id": analysis_id,

        "filename": file.filename,

        "metadata": {

            "duration_seconds": (
                result.metadata.duration_seconds
            ),

            "width": result.metadata.width,

            "height": result.metadata.height,

            "fps": result.metadata.fps,

            "codec": result.metadata.codec,

            "has_audio": result.metadata.has_audio,
        },

        "frames_analyzed": (
            result.frame_count_analyzed
        ),

        "event_count": len(events),

        "events": events,

        "reconstructed_events": (
            reconstructed_events
        ),

        "reconstruction_count": len(
            reconstructed_events
        ),

        "forensic_summary": (
            forensic_summary
        ),

        "integrity_analysis": integrity_analysis,

        "object_disappearance_analysis": (
            object_disappearance_analysis
        ),
    }


# =========================================================
# VIDEO Q&A / CONVERSATIONAL QUERY
# =========================================================

class VideoQueryRequest(BaseModel):
    query: str
    events: list[dict] = []
    summary: dict | None = None


@app.post("/video/query")
def query_video(payload: VideoQueryRequest):
    """
    Answer questions about analyzed video events using Groq or heuristic fallback.
    Matches CLI 'dvrforensics search' and interactive Q&A.
    """
    user_query = payload.query.strip()
    if not user_query:
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    events = payload.events
    summary = payload.summary or {}

    # Try Groq AI first if available
    try:
        from groq import Groq
        import os

        if os.environ.get("GROQ_API_KEY"):
            groq_client = Groq()
            event_lines = []
            for ev in events[:80]:
                e_type = ev.get("event_type", "EVENT")
                obj = ev.get("object_type") or "n/a"
                start = ev.get("start_time", "")
                conf = ev.get("confidence", 0)
                note = (ev.get("metadata") or {}).get("note", "")
                event_lines.append(f"- {e_type} ({obj}) at {start}, conf={conf:.2f} {note}")

            events_context = "\n".join(event_lines) if event_lines else "No specific events."
            headline = summary.get("headline", "")
            overview = summary.get("summary", "")

            system_prompt = (
                "You are an expert digital forensics video analysis assistant. "
                "Answer the investigator's question based strictly on the provided timeline of detected events "
                "and video summary. Mention exact timestamps and object IDs when available. "
                "If not enough evidence exists in the logs, state that clearly."
            )

            prompt = (
                f"Forensic Summary: {headline} — {overview}\n\n"
                f"Detected Events Timeline:\n{events_context}\n\n"
                f"Investigator Question: {user_query}"
            )

            resp = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                max_tokens=400,
                temperature=0.2,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
            )
            answer = resp.choices[0].message.content.strip()

            # Find matching events to highlight in the video timeline
            q_lower = user_query.lower()
            matching_events = [
                ev for ev in events
                if any(w in str(ev.get("event_type", "")).lower() or w in str(ev.get("object_type", "")).lower()
                       for w in q_lower.split() if len(w) > 3)
            ][:10]

            return {
                "answer": answer,
                "matching_events": matching_events,
                "source": "groq",
            }
    except Exception:
        pass

    # Heuristic / Rule-based forensic answer fallback
    q_lower = user_query.lower()
    matched = []
    for ev in events:
        ev_type = str(ev.get("event_type", "")).lower()
        obj_type = str(ev.get("object_type", "")).lower()
        if any(term in q_lower for term in ["person", "people", "human", "who"]) and ("person" in ev_type or "person" in obj_type):
            matched.append(ev)
        elif any(term in q_lower for term in ["car", "vehicle", "truck", "drive"]) and ("vehicle" in ev_type or "vehicle" in obj_type):
            matched.append(ev)
        elif any(term in q_lower for term in ["motion", "movement", "move"]) and "motion" in ev_type:
            matched.append(ev)
        elif any(term in q_lower for term in ["disappear", "lost", "missing", "gone"]) and "disappearance" in ev_type:
            matched.append(ev)

    if not matched and events:
        matched = events[:5]

    if "how many" in q_lower or "count" in q_lower:
        answer = f"Found {len(matched)} matching event(s) matching your query in the forensic timeline."
    elif matched:
        first_time = matched[0].get("start_time", "unknown time")
        answer = f"Detected {len(matched)} event(s) relevant to '{user_query}'. First occurrence observed at {first_time}."
    else:
        answer = f"No events matching '{user_query}' were found in the timeline."

    return {
        "answer": answer,
        "matching_events": matched[:10],
        "source": "heuristic",
    }