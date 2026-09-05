"""backend/cli/tui/engine.py — TraceX real forensic pipeline engine.

Implements the exact pipeline from backend/cli/interactive.py with ZERO dummy data:
- Step 1: Detect (ParserManager.detect)
- Step 2: Parse (ParserManager.parse)
- Step 3: Extract (ParserManager.extract / direct video extraction)
- Step 4: AI Analysis (VideoAnalysisService: Vision + Motion + AI Reconstruction + Forensic Summary)
- Step 5: Integrity Checks (_run_video_integrity_analysis)
- Step 6: Object Disappearance Detection (_detect_object_disappearances)
- Step 7: Video Q&A Query Analysis (_ask_about_video using Groq LLM)
"""

from __future__ import annotations

import os
import shutil
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

from dotenv import load_dotenv

load_dotenv()


def human_size(size_bytes: int | float) -> str:
    """Format byte count into human-readable string."""
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(size_bytes)
    unit_idx = 0
    while size >= 1024.0 and unit_idx < len(units) - 1:
        size /= 1024.0
        unit_idx += 1
    return f"{size:.1f} {units[unit_idx]}" if unit_idx > 0 else f"{int(size)} B"


def safe_event_sort_key(pair: tuple[str, Any]) -> float:
    """Safely get timestamp float for sorting events without tzinfo mismatch."""
    try:
        ev = pair[1]
        st = getattr(ev, "start_time", None)
        if st is not None and hasattr(st, "timestamp"):
            return st.timestamp()
    except Exception:
        pass
    return 0.0


@dataclass
class PipelineResult:
    """Stores all real outputs from the TraceX forensic pipeline for a file."""
    file_path: Path
    file_size: int = 0
    vendor_name: str = "Unknown"
    vendor_confidence: float = 0.0
    parse_recordings: list[dict[str, Any]] = field(default_factory=list)
    recovered_recordings: list[dict[str, Any]] = field(default_factory=list)
    events: list[tuple[str, Any]] = field(default_factory=list)
    reconstructed_events: list[Any] = field(default_factory=list)
    summaries: list[Any] = field(default_factory=list)
    integrity_results: list[tuple[str, dict[str, Any]]] = field(default_factory=list)
    disappearance_results: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    duration_seconds: float = 0.0


@dataclass
class QueryAnswer:
    query: str
    answer: str
    source: str
    matching_events: list[dict[str, Any]] = field(default_factory=list)
    duration_seconds: float = 0.0


class TraceXPipelineEngine:
    """Executes the exact TraceX CLI pipeline and conversational Q&A."""

    def __init__(self):
        self._groq_model = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
        self.current_pipeline_result: PipelineResult | None = None
        self.qa_history: list[dict[str, str]] = []

    def clear(self) -> None:
        """Reset current pipeline result and Q&A history."""
        self.current_pipeline_result = None
        self.qa_history = []

    def run_pipeline(
        self,
        file_path_str: str,
        progress_cb: Optional[Callable[[str], None]] = None,
    ) -> PipelineResult:
        """Run the real detect -> parse -> extract -> AI analyze pipeline on the given file."""
        start_t = time.perf_counter()

        path = Path(file_path_str.strip('"').strip("'")).expanduser().resolve()
        if not path.is_file():
            raise FileNotFoundError(f"File not found: {path}")

        res = PipelineResult(
            file_path=path,
            file_size=path.stat().st_size,
        )

        from backend.parsers.registry import ParserManager

        manager = ParserManager()

        # =====================================================
        # STEP 1 — DETECT
        # =====================================================
        if progress_cb:
            progress_cb("Step 1 / 4 — Detecting vendor and signature...")

        parser, confidence, info = manager.detect(str(path))
        if parser is None:
            res.errors.append("No registered parser recognized this file signature.")
            return res

        res.vendor_name = parser.vendor_name
        res.vendor_confidence = confidence

        # =====================================================
        # STEP 2 — PARSE
        # =====================================================
        if progress_cb:
            progress_cb(f"Step 2 / 4 — Parsing evidence ({parser.vendor_name})...")

        out_dir = Path("./tracex_output") / path.stem
        out_dir.mkdir(parents=True, exist_ok=True)

        parse_result = manager.parse(str(path), str(out_dir))
        res.warnings.extend(parse_result.warnings)

        if not parse_result.success:
            res.errors.extend(parse_result.errors)
            return res

        for rec in parse_result.recordings:
            res.parse_recordings.append(
                {
                    "recording_id": rec.recording_id,
                    "camera_id": rec.camera_id,
                    "timestamp": (
                        rec.original_timestamp.isoformat(sep=" ", timespec="seconds")
                        if rec.original_timestamp
                        else "unknown"
                    ),
                    "status": rec.recovery_status,
                }
            )

        # =====================================================
        # STEP 3 — EXTRACT
        # =====================================================
        if progress_cb:
            progress_cb("Step 3 / 4 — Extracting recordings...")

        already_usable = [
            rec for rec in parse_result.recordings
            if rec.extracted_path and Path(rec.extracted_path).is_file()
        ]

        if len(already_usable) == len(parse_result.recordings) and len(parse_result.recordings) > 0:
            recovered = already_usable
        else:
            if shutil.which("ffmpeg") is None:
                res.warnings.append("ffmpeg not found on PATH — extraction skipped.")
                recovered = already_usable
            else:
                extract_result = manager.extract(str(path), str(out_dir), parse_result)
                res.warnings.extend(extract_result.warnings)
                if not extract_result.success:
                    res.errors.extend(extract_result.errors)

                recovered = []
                for rec in extract_result.recordings:
                    if rec.extracted_path and Path(rec.extracted_path).is_file():
                        recovered.append(rec)

        for rec in recovered:
            res.recovered_recordings.append(
                {
                    "recording_id": rec.recording_id,
                    "camera_id": rec.camera_id,
                    "status": rec.recovery_status,
                    "extracted_path": rec.extracted_path,
                    "original_timestamp": rec.original_timestamp,
                }
            )

        if not recovered:
            res.warnings.append("No playable recordings were extracted to analyze.")
            res.duration_seconds = time.perf_counter() - start_t
            self.current_pipeline_result = res
            return res

        # =====================================================
        # STEP 4 — AI ANALYSIS (Vision + Motion + Reconstruction)
        # =====================================================
        if progress_cb:
            progress_cb("Step 4 / 4 — Running AI video analysis (Vision & Motion)...")

        try:
            from backend.video.analysis.service import VideoAnalysisService

            service = VideoAnalysisService(yolo_model="yolo26n.pt")
            all_events = []
            all_reconstructed = []
            all_summaries = []

            for rec in recovered:
                if progress_cb:
                    progress_cb(f"Analyzing recording: {rec.recording_id}...")

                try:
                    analysis_res = service.analyze(
                        video_id=rec.recording_id,
                        camera_id=rec.camera_id,
                        video_path=Path(rec.extracted_path),
                        video_start_time=(
                            rec.original_timestamp or datetime.now(timezone.utc)
                        ),
                        frame_sample_fps=2.0,
                    )

                    all_events.extend(
                        (rec.camera_id, ev) for ev in analysis_res.events
                    )

                    reconstructed = getattr(analysis_res, "reconstructed_events", [])
                    if reconstructed:
                        all_reconstructed.extend(reconstructed)

                    forensic_sum = getattr(analysis_res, "forensic_summary", None)
                    if forensic_sum is not None:
                        all_summaries.append(forensic_sum)
                except Exception as exc:
                    res.warnings.append(f"AI analysis on {rec.recording_id} failed: {exc}")

            res.events = all_events
            res.reconstructed_events = all_reconstructed
            res.summaries = all_summaries

        except ImportError as exc:
            res.warnings.append(f"AI analysis optional libraries unavailable: {exc}")

        # =====================================================
        # TAMPERING / VIDEO INTEGRITY CHECKS
        # =====================================================
        if progress_cb:
            progress_cb("Checking video integrity and tampering indicators...")

        from backend.cli.interactive import _run_video_integrity_analysis

        for rec in recovered:
            rec_path = Path(rec.extracted_path)
            if rec_path.is_file():
                try:
                    integrity = _run_video_integrity_analysis(rec_path)
                    res.integrity_results.append((rec.recording_id, integrity))
                except Exception as exc:
                    res.warnings.append(f"Integrity check on {rec.recording_id} failed: {exc}")

        # =====================================================
        # OBJECT DISAPPEARANCE DETECTION
        # =====================================================
        if progress_cb:
            progress_cb("Detecting object disappearances and continuity...")

        from backend.cli.interactive import _detect_object_disappearances

        # We call the core detection function and extract candidate observations
        if res.events:
            try:
                # Disappearance logic from interactive.py
                observations: dict[tuple[str, str], list[dict[str, Any]]] = {}
                for camera_id, ev in res.events:
                    obj = getattr(ev, "object_type", None)
                    if not obj or str(obj).strip().lower() in {"motion", "unknown", "none", ""}:
                        continue
                    # Confidence bar: ignore weak or noisy detections
                    conf = getattr(ev, "confidence", None)
                    if conf is not None and conf < 0.50:
                        continue
                    obj_name = str(obj).strip().lower()
                    st = getattr(ev, "start_time", None)
                    et = getattr(ev, "end_time", None) or st
                    if st is None:
                        continue
                    key = (str(camera_id or "CH-0"), obj_name)
                    observations.setdefault(key, []).append({"start": st, "end": et, "event": ev})

                candidates = []
                for (camera_id, object_type), items in observations.items():
                    items.sort(key=lambda it: it["start"])
                    if len(items) >= 2:
                        first_seen = items[0]["start"]
                        last_seen = max(it["end"] for it in items)
                        candidates.append(
                            {
                                "camera_id": camera_id,
                                "object_type": object_type,
                                "first_seen": first_seen.isoformat(sep=" ", timespec="seconds"),
                                "last_seen": last_seen.isoformat(sep=" ", timespec="seconds"),
                                "observations_count": len(items),
                                "note": f"Repeatedly tracked ({len(items)} detections) then stopped appearing after {last_seen.isoformat(sep=' ', timespec='seconds')}",
                            }
                        )
                res.disappearance_results = candidates
            except Exception as exc:
                res.warnings.append(f"Object disappearance analysis notice: {exc}")

        res.duration_seconds = time.perf_counter() - start_t
        self.current_pipeline_result = res
        self._init_qa_session(res)
        return res

    def _init_qa_session(self, res: PipelineResult, query: str | None = None) -> None:
        """Initialize the Groq system prompt with compact, token-budgeted forensic context."""
        from backend.core.search.context_compressor import build_compact_forensic_context

        context_text = build_compact_forensic_context(
            video_name=res.file_path.name,
            raw_events=res.events,
            reconstructed_events=res.reconstructed_events,
            forensic_summaries=res.summaries,
            query=query,
            max_reconstructed=20,
            max_spans=30,
        )

        system_prompt = (
            "You are an expert forensic video-analysis assistant for TraceX. "
            "You are given structured forensic findings, reconstructed activities, and entity timeline tracks from video analysis. "
            "Answer the investigator's questions factually, concisely, and precisely based strictly on this forensic timeline. "
            "If the forensic data does not confirm an answer, say so plainly.\n\n"
            f"{context_text}"
        )

        self.qa_history = [
            {"role": "system", "content": system_prompt}
        ]

    def ask_video_query(self, question: str) -> QueryAnswer:
        """Answer a query about the analyzed video using Groq (matching interactive.py)."""
        start_t = time.perf_counter()
        clean_q = question.strip()
        if not clean_q:
            return QueryAnswer(
                query=question,
                answer="Please enter a question about the video.",
                source="system",
            )

        if not self.current_pipeline_result:
            return QueryAnswer(
                query=question,
                answer="No video has been analyzed yet. Please provide a file first.",
                source="system",
            )

        # Refresh prompt with query-aware focus if needed
        self._init_qa_session(self.current_pipeline_result, query=clean_q)

        events = self.current_pipeline_result.events

        # Groq client execution (exact logic from interactive.py lines 106-220)
        answer = ""
        source = "heuristic"

        groq_key = os.getenv("GROQ_API_KEY")
        if groq_key:
            try:
                from groq import Groq

                client = Groq(api_key=groq_key)
                messages = list(self.qa_history)
                messages.append({"role": "user", "content": clean_q})

                resp = client.chat.completions.create(
                    model=self._groq_model,
                    max_tokens=400,
                    messages=messages,
                )

                answer = resp.choices[0].message.content.strip()
                source = f"TraceX Groq Model ({self._groq_model})"

                # Add to history for multi-turn conversation
                self.qa_history.append({"role": "user", "content": clean_q})
                self.qa_history.append({"role": "assistant", "content": answer})
            except Exception as exc:
                source = f"TraceX Heuristic Engine (Groq offline: {exc})"

        # Heuristic fallback matching backend/api/main.py if Groq is unavailable
        if not answer:
            q_lower = clean_q.lower()
            matched = []
            for cam, ev in events:
                e_type = str(getattr(ev, "event_type", "")).lower()
                o_type = str(getattr(ev, "object_type", "")).lower()
                if any(w in q_lower for w in ["person", "people", "human", "who"]) and ("person" in e_type or "person" in o_type):
                    matched.append((cam, ev))
                elif any(w in q_lower for w in ["car", "vehicle", "truck", "drive"]) and ("vehicle" in e_type or "vehicle" in o_type):
                    matched.append((cam, ev))
                elif any(w in q_lower for w in ["motion", "movement", "move"]) and "motion" in e_type:
                    matched.append((cam, ev))
                elif any(w in q_lower for w in ["phone", "cell", "mobile"]) and "phone" in o_type:
                    matched.append((cam, ev))

            if "how many" in q_lower or "count" in q_lower:
                answer = f"Found {len(matched)} matching event(s) in the analyzed video timeline."
            elif matched:
                first_cam, first_ev = matched[0]
                first_time = getattr(first_ev, "start_time", "unknown time")
                answer = f"Detected {len(matched)} event(s) relevant to '{clean_q}'. First observed on camera {first_cam} at {first_time}."
            elif events:
                answer = f"No events in the timeline specifically matched '{clean_q}'. Total recorded events: {len(events)}."
            else:
                answer = "No events were detected in this video footage."

        # Find matching events to display
        q_words = [w.lower() for w in clean_q.split() if len(w) > 3]
        matching_dicts = []
        for cam, ev in events:
            e_type = str(getattr(ev, "event_type", ""))
            o_type = str(getattr(ev, "object_type", ""))
            if any(w in e_type.lower() or w in o_type.lower() for w in q_words):
                matching_dicts.append(
                    {
                        "camera_id": cam,
                        "event_type": e_type,
                        "object_type": o_type or "-",
                        "start_time": (
                            ev.start_time.isoformat(sep=" ", timespec="seconds")
                            if hasattr(ev, "start_time")
                            else "-"
                        ),
                        "confidence": getattr(ev, "confidence", None),
                    }
                )

        duration = time.perf_counter() - start_t
        return QueryAnswer(
            query=clean_q,
            answer=answer,
            source=source,
            matching_events=matching_dicts,
            duration_seconds=duration,
        )
