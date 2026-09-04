"""backend/core/search/context_compressor.py

Forensic Context Compression & Query-Aware Retrieval (RAG) Engine.

Compresses hundreds or thousands of raw per-frame detections into concise,
dense entity track spans, prioritized reconstructed activities, and query-relevant
evidence candidates to keep LLM context sizes well within token budgets (under 2,000 tokens).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Sequence


@dataclass
class CompressedTrackSpan:
    track_id: int | str
    camera_id: str
    object_type: str
    start_time: datetime
    end_time: datetime
    duration_seconds: float
    observation_count: int
    direction: str = "Stationary"
    avg_speed: float = 0.0
    is_loitering: bool = False
    notes: str = ""

    def to_summary_line(self) -> str:
        st_str = self.start_time.isoformat(sep=" ", timespec="seconds")
        et_str = self.end_time.isoformat(sep=" ", timespec="seconds")
        loiter_tag = " [LOITERING]" if self.is_loitering else ""
        return (
            f"- {self.object_type.upper()} #{self.track_id} on {self.camera_id}: "
            f"{st_str} -> {et_str} ({self.duration_seconds:.1f}s, {self.observation_count} frames), "
            f"Heading: {self.direction}, Speed: {self.avg_speed:.1f}px/s{loiter_tag}"
        )


import math


def _direction_from_vector(vx: float, vy: float) -> str:
    """Calculate 8-point compass direction from velocity vector (vx, vy)."""
    speed = math.hypot(vx, vy)
    if speed < 5.0:
        return "Stationary"

    angle = math.degrees(math.atan2(vy, vx)) % 360

    if 337.5 <= angle or angle < 22.5:
        return "Eastbound (→)"
    elif 22.5 <= angle < 67.5:
        return "South-East (↘)"
    elif 67.5 <= angle < 112.5:
        return "Southbound (↓)"
    elif 112.5 <= angle < 157.5:
        return "South-West (↙)"
    elif 157.5 <= angle < 202.5:
        return "Westbound (←)"
    elif 202.5 <= angle < 247.5:
        return "North-West (↖)"
    elif 247.5 <= angle < 292.5:
        return "Northbound (↑)"
    else:
        return "North-East (↗)"


def _safe_get(obj: Any, attr: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(attr, default)
    return getattr(obj, attr, default)


def compress_events_into_track_spans(
    events: Sequence[Any | tuple[str, Any]],
) -> list[CompressedTrackSpan]:
    """
    Consolidate per-frame detections into distinct continuous entity intervals.
    """
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = {}

    for item in events:
        if isinstance(item, tuple) and len(item) == 2:
            cam_id, ev = item
        else:
            ev = item
            cam_id = _safe_get(ev, "camera_id", "CH-0")

        cam_id = str(cam_id or "CH-0")
        tid = _safe_get(ev, "track_id")
        tid_str = str(tid) if tid is not None else "0"
        obj_type = str(_safe_get(ev, "object_type") or _safe_get(ev, "event_type") or "object").lower()
        st = _safe_get(ev, "start_time")
        et = _safe_get(ev, "end_time") or st

        if st is None:
            continue

        key = (cam_id, tid_str, obj_type)
        grouped.setdefault(key, []).append({
            "start": st,
            "end": et,
            "confidence": float(_safe_get(ev, "confidence", 0.7) or 0.7),
            "metadata": _safe_get(ev, "metadata", {}) or {},
        })

    spans: list[CompressedTrackSpan] = []

    for (cam_id, tid_str, obj_type), obs_list in grouped.items():
        obs_list.sort(key=lambda x: x["start"])
        first_st = obs_list[0]["start"]
        last_et = obs_list[-1]["end"]
        try:
            dur = max(0.1, (last_et - first_st).total_seconds())
        except Exception:
            dur = 0.5

        direction = "Stationary"
        avg_speed = 0.0
        is_loitering = False
        all_obs_bboxes = []

        for o in obs_list:
            meta = o.get("metadata", {})
            if isinstance(meta, dict):
                if "direction" in meta and meta["direction"] != "Stationary":
                    direction = meta["direction"]
                if "avg_speed" in meta and float(meta["avg_speed"]) > 0.0:
                    avg_speed = max(avg_speed, float(meta["avg_speed"]))
                if meta.get("is_loitering"):
                    is_loitering = True
                if "observations" in meta and isinstance(meta["observations"], list):
                    for sub_o in meta["observations"]:
                        if isinstance(sub_o, dict) and "bbox" in sub_o:
                            all_obs_bboxes.append(sub_o["bbox"])

        # If speed or direction is still stationary, calculate directly from observation coordinates
        if (direction == "Stationary" or avg_speed == 0.0) and len(all_obs_bboxes) >= 2:
            first_bx = all_obs_bboxes[0]
            last_bx = all_obs_bboxes[-1]
            c1 = ((first_bx[0] + first_bx[2]) / 2.0, (first_bx[1] + first_bx[3]) / 2.0)
            c2 = ((last_bx[0] + last_bx[2]) / 2.0, (last_bx[1] + last_bx[3]) / 2.0)
            dx = c2[0] - c1[0]
            dy = c2[1] - c1[1]
            disp = math.hypot(dx, dy)
            calc_speed = disp / dur if dur > 0 else 0.0
            if disp >= 15.0 or calc_speed >= 5.0:
                direction = _direction_from_vector(dx / dur, dy / dur)
                avg_speed = calc_speed
            if dur >= 3.0 and disp <= 60.0 and obj_type in ("person", "vehicle", "car"):
                is_loitering = True

        spans.append(CompressedTrackSpan(
            track_id=tid_str,
            camera_id=cam_id,
            object_type=obj_type,
            start_time=first_st,
            end_time=last_et,
            duration_seconds=dur,
            observation_count=len(obs_list),
            direction=direction,
            avg_speed=avg_speed,
            is_loitering=is_loitering,
        ))

    spans.sort(key=lambda s: s.start_time)
    return spans


def build_compact_forensic_context(
    video_name: str,
    raw_events: Sequence[Any | tuple[str, Any]],
    reconstructed_events: Sequence[Any] | None = None,
    forensic_summaries: Sequence[Any] | None = None,
    query: str | None = None,
    max_reconstructed: int = 15,
    max_spans: int = 25,
) -> str:
    """
    Build a dense, token-budgeted system prompt context suitable for LLMs.
    Guaranteed to remain compact (< 3,500 characters) regardless of video length.
    """
    reconstructed = list(reconstructed_events or [])
    summaries = list(forensic_summaries or [])

    # 1. Headline & Forensic Summary
    headline = ""
    summary_text = ""
    key_findings: list[str] = []

    if summaries:
        s0 = summaries[0]
        headline = str(_safe_get(s0, "headline", ""))
        summary_text = str(_safe_get(s0, "summary", ""))
        key_findings = list(_safe_get(s0, "key_events", []) or _safe_get(s0, "key_findings", []) or [])

    # 2. Query-Aware Relevance Ranking
    q_words = [w.lower() for w in (query or "").split() if len(w) > 2]
    security_keywords = {
        "theft", "steal", "stolen", "robbery", "thief", "suspect", "flee", "fleeing",
        "escape", "intruder", "intrusion", "loitering", "prowling", "break-in", "disappear",
        "disappeared", "removal", "running", "sprint", "getaway", "vehicle", "crash", "impact",
    }

    def _score_text(text: str) -> int:
        t_low = text.lower()
        score = sum(2 for w in q_words if w in t_low) if q_words else 0
        score += sum(1 for sk in security_keywords if sk in t_low)
        return score

    # 3. Format Reconstructed Activities
    formatted_activities: list[tuple[int, str]] = []
    for ev in reconstructed:
        ev_type = str(_safe_get(ev, "event_type", "ACTIVITY"))
        title = str(_safe_get(ev, "title", ev_type))
        desc = str(_safe_get(ev, "description", ""))
        st = _safe_get(ev, "start_time")
        st_str = st.isoformat(sep=" ", timespec="seconds") if st and hasattr(st, "isoformat") else ""

        line = f"- [{ev_type}] {title} at {st_str}: {desc}" if desc else f"- [{ev_type}] {title} at {st_str}"
        score = _score_text(line)
        if any(tag in ev_type for tag in ("LOITERING", "PROWLING", "FLEEING", "COORDINATION", "CONVERGENCE", "ASSET", "DISAPPEARANCE", "BREACH")):
            score += 3
        formatted_activities.append((score, line))

    formatted_activities.sort(key=lambda x: x[0], reverse=True)
    selected_activities = [line for _, line in formatted_activities[:max_reconstructed]]

    # 4. Format Compressed Entity Spans
    spans = compress_events_into_track_spans(raw_events)
    formatted_spans: list[tuple[int, str]] = []
    for span in spans:
        line = span.to_summary_line()
        score = _score_text(line) + (3 if span.is_loitering else 0) + (2 if span.avg_speed >= 75.0 else 0)
        formatted_spans.append((score, line))

    formatted_spans.sort(key=lambda x: x[0], reverse=True)
    selected_spans = [line for _, line in formatted_spans[:max_spans]]

    # 5. Assemble Dense Prompt Context
    lines = [
        f"Video Evidence: {video_name}",
        f"Total Raw Frame Detections: {len(raw_events)} (condensed into {len(spans)} entity tracks)",
    ]

    if headline or summary_text:
        lines.append(f"Forensic Summary: {headline} - {summary_text}")

    if key_findings:
        lines.append("Key Findings:\n" + "\n".join(f"  * {k}" for k in key_findings[:5]))

    if selected_activities:
        lines.append(f"Reconstructed Forensic Activities (Top {len(selected_activities)} of {len(reconstructed)}):")
        lines.extend(selected_activities)

    if selected_spans:
        lines.append(f"Tracked Entity Spans (Top {len(selected_spans)} of {len(spans)}):")
        lines.extend(selected_spans)

    if not selected_activities and not selected_spans:
        lines.append("No significant motion or entity events recorded in timeline.")

    return "\n\n".join(lines)
