"""FastAPI app for the DVR Forensics Platform."""

from datetime import datetime, timezone
from pathlib import Path
import json
import os
import shutil
import subprocess
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
# WEB VIDEO NORMALIZATION
# =========================================================

def _run_video_command(command: list[str], timeout: int = 1800) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='replace', timeout=timeout, check=False)
    except FileNotFoundError as exc:
        raise RuntimeError("FFmpeg/FFprobe is not installed or is not available on PATH.") from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("Video processing timed out.") from exc

def _probe_uploaded_video(video_path: Path) -> dict:
    if not video_path.is_file():
        raise FileNotFoundError(str(video_path))
    completed = _run_video_command(["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(video_path)], 120)
    if completed.returncode != 0:
        raise ValueError("The uploaded file is not a readable video: " + (completed.stderr.strip() or "FFprobe could not read the file."))
    try:
        probe = json.loads(completed.stdout or "{}")
    except json.JSONDecodeError as exc:
        raise ValueError("FFprobe returned invalid video metadata.") from exc
    streams = probe.get("streams") or []
    videos = [x for x in streams if x.get("codec_type") == "video"]
    if not videos:
        raise ValueError("The uploaded file does not contain a video stream.")
    stream = videos[0]; fmt = probe.get("format") or {}
    return {"format_name": fmt.get("format_name"), "format_long_name": fmt.get("format_long_name"), "duration": fmt.get("duration"), "size": fmt.get("size"), "video_codec": stream.get("codec_name"), "width": stream.get("width"), "height": stream.get("height"), "fps": stream.get("r_frame_rate") or stream.get("avg_frame_rate"), "has_audio": any(x.get("codec_type") == "audio" for x in streams)}

def _normalize_uploaded_video(source_path: Path, output_path: Path) -> dict:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    completed = _run_video_command(["ffmpeg", "-y", "-i", str(source_path), "-map", "0:v:0", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-map", "0:a:0?", "-c:a", "aac", "-b:a", "192k", str(output_path)], 1800)
    if completed.returncode != 0:
        raise RuntimeError("Video normalization failed: " + (completed.stderr.strip() or "FFmpeg failed to create the MP4."))
    if not output_path.is_file() or output_path.stat().st_size <= 0:
        raise RuntimeError("FFmpeg did not create a valid normalized MP4.")
    return _probe_uploaded_video(output_path)

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

@app.post("/video/analyze")
async def analyze_video(file: UploadFile = File(...), user: AuthenticatedUser | None = Depends(get_current_user)):
    """Analyze any FFmpeg-readable video without modifying the original upload."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename supplied")
    analysis_id = str(uuid.uuid4())
    directory = Path("backend") / "storage" / "video_analysis" / analysis_id
    directory.mkdir(parents=True, exist_ok=True)
    original_name = Path(file.filename).name
    extension = Path(original_name).suffix.lower() or ".bin"
    original_path = directory / f"original{extension}"
    normalized_path = directory / "normalized.mp4"
    try:
        with open(original_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer, length=1024 * 1024)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to save uploaded video: {exc}") from exc
    finally:
        await file.close()
    try:
        original_probe = _probe_uploaded_video(original_path)
        normalized_probe = _normalize_uploaded_video(original_path, normalized_path)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    try:
        result = video_analysis_service.analyze(video_id=analysis_id, camera_id="camera_01", video_path=normalized_path, video_start_time=datetime.now(timezone.utc), frame_sample_fps=5.0)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Video analysis failed: {exc}") from exc
    events = [{"event_type": e.event_type, "video_id": e.video_id, "camera_id": e.camera_id, "start_time": e.start_time.isoformat(), "end_time": e.end_time.isoformat(), "confidence": e.confidence, "track_id": e.track_id, "object_type": e.object_type, "metadata": e.metadata} for e in result.events]
    reconstructed_events = [{"video_id": e.video_id, "camera_id": e.camera_id, "event_type": e.event_type, "start_time": e.start_time.isoformat(), "end_time": e.end_time.isoformat(), "title": e.title, "description": e.description, "objects": e.objects, "confidence": e.confidence, "metadata": e.metadata} for e in result.reconstructed_events]
    summary = result.forensic_summary
    forensic_summary = {"video_id": summary.video_id, "camera_id": summary.camera_id, "start_time": summary.start_time.isoformat() if summary.start_time else None, "end_time": summary.end_time.isoformat() if summary.end_time else None, "headline": summary.headline, "summary": summary.summary, "key_events": summary.key_events, "objects_detected": summary.objects_detected, "event_count": summary.event_count, "confidence": summary.confidence, "metadata": summary.metadata}
    integrity_analysis = _build_integrity_response(normalized_path)
    object_disappearance_analysis = _build_object_disappearance_response(result.events)
    return {"status": "success", "analysis_id": analysis_id, "filename": file.filename, "normalization": {"original_filename": file.filename, "original_extension": extension, "original_format": original_probe.get("format_name"), "original_format_long_name": original_probe.get("format_long_name"), "normalized": True, "normalized_filename": "normalized.mp4", "original_path": str(original_path), "normalized_path": str(normalized_path), "original_metadata": original_probe, "normalized_metadata": normalized_probe}, "metadata": {"duration_seconds": result.metadata.duration_seconds, "width": result.metadata.width, "height": result.metadata.height, "fps": result.metadata.fps, "codec": result.metadata.codec, "has_audio": result.metadata.has_audio}, "frames_analyzed": result.frame_count_analyzed, "event_count": len(events), "events": events, "reconstructed_events": reconstructed_events, "reconstruction_count": len(reconstructed_events), "forensic_summary": forensic_summary, "integrity_analysis": integrity_analysis, "object_disappearance_analysis": object_disappearance_analysis}

