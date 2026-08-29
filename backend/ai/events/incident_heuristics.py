
"""backend/ai/events/incident_heuristics.py — explainable incident-candidate flags.

This is deliberately NOT an "accident detector." YOLO detections carry no
temporal/causal information on their own — event_builder.py only groups a
single track's consecutive detections into a span. This module adds two
narrow, explainable heuristics on top of the same per-frame Detection data
build_detection_events() already consumes, and emits *review flags* —
never assertions of fact. Every emitted event's metadata explains exactly
why it was flagged, so an investigator can pull up that timestamp and
judge it themselves. Meant to run alongside build_detection_events(), not
replace it.
"""

from __future__ import annotations

from collections import defaultdict
from itertools import combinations

from backend.video.analysis.models import Detection, VideoEvent


def _iou(box_a: tuple[float, float, float, float], box_b: tuple[float, float, float, float]) -> float:
    """Intersection-over-union for two (x1, y1, x2, y2) boxes."""
    ax1, ay1, ax2, ay2 = box_a
    bx1, by1, bx2, by2 = box_b

    inter_x1 = max(ax1, bx1)
    inter_y1 = max(ay1, by1)
    inter_x2 = min(ax2, bx2)
    inter_y2 = min(ay2, by2)

    inter_w = max(0.0, inter_x2 - inter_x1)
    inter_h = max(0.0, inter_y2 - inter_y1)
    inter_area = inter_w * inter_h
    if inter_area <= 0:
        return 0.0

    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    union = area_a + area_b - inter_area
    if union <= 0:
        return 0.0
    return inter_area / union


def _bbox_center(box: tuple[float, float, float, float]) -> tuple[float, float]:
    x1, y1, x2, y2 = box
    return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)


def detect_proximity_events(
    detections: list[Detection],
    iou_threshold: float = 0.15,
    collision_iou_threshold: float = 0.35,
) -> list[VideoEvent]:
    """Flag moments where two *different* tracked objects' bounding boxes
    overlap significantly. This is a proximity signal only — bbox overlap
    in a 2D projection does not prove physical contact (a person could be
    walking behind a car, not into it). Always emitted as a review flag.
    """
    by_frame: dict[int, list[Detection]] = defaultdict(list)
    for d in detections:
        if d.track_id is not None:
            by_frame[d.frame_number].append(d)

    events: list[VideoEvent] = []
    seen_pairs: set[tuple[int, int, int]] = set()  # (frame, track_a, track_b)

    for frame_number, frame_detections in by_frame.items():
        for det_a, det_b in combinations(frame_detections, 2):
            if det_a.track_id == det_b.track_id:
                continue
            if det_a.camera_id != det_b.camera_id:
                continue

            iou = _iou(det_a.bbox, det_b.bbox)
            if iou < iou_threshold:
                continue

            pair_key = (frame_number, min(det_a.track_id, det_b.track_id), max(det_a.track_id, det_b.track_id))
            if pair_key in seen_pairs:
                continue
            seen_pairs.add(pair_key)

            severity = "POSSIBLE_CONTACT" if iou >= collision_iou_threshold else "PROXIMITY"
            events.append(
                VideoEvent(
                    video_id=det_a.video_id,
                    camera_id=det_a.camera_id,
                    event_type=f"REVIEW_FLAG_{severity}",
                    start_time=det_a.timestamp,
                    end_time=det_a.timestamp,
                    confidence=round(iou, 2),
                    metadata={
                        "reason": "bounding_box_overlap",
                        "object_a": det_a.object_type,
                        "track_a": det_a.track_id,
                        "object_b": det_b.object_type,
                        "track_b": det_b.track_id,
                        "iou": round(iou, 3),
                        "note": (
                            "Flagged for human review only. Bounding-box overlap in a 2D "
                            "frame does not confirm physical contact or a collision — it "
                            "means these two tracked objects' boxes overlapped on screen."
                        ),
                    },
                )
            )

    return events


def detect_sudden_stop_events(
    detections: list[Detection],
    min_points: int = 4,
    speed_drop_ratio: float = 0.6,
    moving_speed_floor: float = 5.0,
) -> list[VideoEvent]:
    """Flag a single track whose frame-to-frame speed drops sharply after
    having established it was moving. A candidate for "sudden stop" —
    could be braking, could be an obstruction, could just be the object
    leaving frame at an angle. Always emitted as a review flag, not fact.
    """
    by_track: dict[tuple[str, int], list[Detection]] = defaultdict(list)
    for d in detections:
        if d.track_id is not None:
            by_track[(d.camera_id, d.track_id)].append(d)

    events: list[VideoEvent] = []

    for (camera_id, track_id), track_detections in by_track.items():
        track_detections.sort(key=lambda d: d.timestamp)
        if len(track_detections) < min_points:
            continue

        speeds = []  # (detection, speed_px_per_sec)
        for prev, curr in zip(track_detections, track_detections[1:]):
            dt = (curr.timestamp - prev.timestamp).total_seconds()
            if dt <= 0:
                continue
            cx1, cy1 = _bbox_center(prev.bbox)
            cx2, cy2 = _bbox_center(curr.bbox)
            dist = ((cx2 - cx1) ** 2 + (cy2 - cy1) ** 2) ** 0.5
            speeds.append((curr, dist / dt))

        for i in range(1, len(speeds)):
            prev_det, prev_speed = speeds[i - 1]
            curr_det, curr_speed = speeds[i]

            if prev_speed < moving_speed_floor:
                continue  # wasn't clearly moving to begin with

            if curr_speed <= prev_speed * (1 - speed_drop_ratio):
                events.append(
                    VideoEvent(
                        video_id=curr_det.video_id,
                        camera_id=camera_id,
                        event_type="REVIEW_FLAG_SUDDEN_STOP",
                        start_time=prev_det.timestamp,
                        end_time=curr_det.timestamp,
                        confidence=curr_det.confidence,
                        track_id=track_id,
                        object_type=curr_det.object_type,
                        metadata={
                            "reason": "sharp_deceleration",
                            "speed_before_px_per_sec": round(prev_speed, 1),
                            "speed_after_px_per_sec": round(curr_speed, 1),
                            "note": (
                                "Flagged for human review only. This tracked object's "
                                "on-screen speed dropped sharply — could be braking, an "
                                "obstruction, a turn, or the object leaving frame. Does "
                                "not confirm an incident."
                            ),
                        },
                    )
                )

    return events


def detect_incident_candidates(detections: list[Detection]) -> list[VideoEvent]:
    """Convenience wrapper combining both heuristics."""
    return detect_proximity_events(detections) + detect_sudden_stop_events(detections)