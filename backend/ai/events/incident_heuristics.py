"""backend/ai/events/incident_heuristics.py — explainable incident-candidate flags.

Emits review flags for forensic investigation:
1. Multi-vehicle proximity and contact (IoU overlap and edge-to-edge distance).
2. Dashcam / ego-vehicle crash candidates (rapid optical looming and close foreground approach).
3. Sudden deceleration and stopping upon impact.
"""

from __future__ import annotations

from collections import defaultdict
from itertools import combinations
import math

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


def _box_distance(box_a: tuple[float, float, float, float], box_b: tuple[float, float, float, float]) -> float:
    """Euclidean edge-to-edge distance between two (x1, y1, x2, y2) boxes. 0.0 if overlapping."""
    ax1, ay1, ax2, ay2 = box_a
    bx1, by1, bx2, by2 = box_b
    dx = max(0.0, max(ax1, bx1) - min(ax2, bx2))
    dy = max(0.0, max(ay1, by1) - min(ay2, by2))
    return float(math.hypot(dx, dy))


def _bbox_center(box: tuple[float, float, float, float]) -> tuple[float, float]:
    x1, y1, x2, y2 = box
    return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)


def detect_proximity_events(
    detections: list[Detection],
    iou_threshold: float = 0.05,
    collision_iou_threshold: float = 0.15,
    max_edge_distance_px: float = 40.0,
    contact_edge_distance_px: float = 15.0,
) -> list[VideoEvent]:
    """Flag moments where two *different* tracked objects' bounding boxes
    overlap significantly or come into direct edge-to-edge contact.
    Always emitted as a review flag.
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
            edge_dist = _box_distance(det_a.bbox, det_b.bbox)

            is_contact = (iou >= collision_iou_threshold) or (edge_dist <= contact_edge_distance_px)
            is_proximity = (iou >= iou_threshold) or (edge_dist <= max_edge_distance_px)

            if not is_proximity and not is_contact:
                continue

            pair_key = (frame_number, min(det_a.track_id, det_b.track_id), max(det_a.track_id, det_b.track_id))
            if pair_key in seen_pairs:
                continue
            seen_pairs.add(pair_key)

            severity = "POSSIBLE_CONTACT" if is_contact else "PROXIMITY"
            confidence_score = round(max(iou, max(0.0, 1.0 - edge_dist / max_edge_distance_px)), 2)

            events.append(
                VideoEvent(
                    video_id=det_a.video_id,
                    camera_id=det_a.camera_id,
                    event_type=f"REVIEW_FLAG_{severity}",
                    start_time=det_a.timestamp,
                    end_time=det_a.timestamp,
                    confidence=max(0.5, confidence_score),
                    metadata={
                        "reason": "bounding_box_overlap_or_edge_contact",
                        "object_a": det_a.object_type,
                        "track_a": det_a.track_id,
                        "object_b": det_b.object_type,
                        "track_b": det_b.track_id,
                        "iou": round(iou, 3),
                        "edge_distance_px": round(edge_dist, 1),
                        "note": (
                            "Flagged for human review. Direct bounding-box overlap or edge "
                            "proximity detected between two tracked entities on screen."
                        ),
                    },
                )
            )

    return events


def detect_ego_collision_events(
    detections: list[Detection],
    min_expansion_ratio: float = 1.35,
    min_expansion_rate_px: float = 25.0,
) -> list[VideoEvent]:
    """Flag dashcam / ego-vehicle crash candidates where a vehicle in front of the camera
    expands rapidly in size (rapid looming) and approaches the front bumper / bottom frame edge.
    """
    by_track: dict[tuple[str, int], list[Detection]] = defaultdict(list)
    for d in detections:
        if d.track_id is not None and d.object_type in ("car", "vehicle", "truck", "bus", "motorcycle"):
            by_track[(d.camera_id, d.track_id)].append(d)

    events: list[VideoEvent] = []

    for (camera_id, track_id), track_detections in by_track.items():
        if len(track_detections) < 2:
            continue
        track_detections.sort(key=lambda d: d.timestamp)

        for i in range(1, len(track_detections)):
            prev = track_detections[i - 1]
            curr = track_detections[i]
            dt = max(0.05, (curr.timestamp - prev.timestamp).total_seconds())

            prev_w = max(1.0, prev.bbox[2] - prev.bbox[0])
            prev_h = max(1.0, prev.bbox[3] - prev.bbox[1])
            curr_w = max(1.0, curr.bbox[2] - curr.bbox[0])
            curr_h = max(1.0, curr.bbox[3] - curr.bbox[1])

            prev_area = prev_w * prev_h
            curr_area = curr_w * curr_h
            area_ratio = curr_area / max(1.0, prev_area)

            expansion_rate = (curr_w - prev_w) / dt

            # Foreground proximity (bottom edge y2 or large bounding box area)
            curr_bottom = curr.bbox[3]
            is_foreground = curr_bottom >= 180.0 or curr_area >= 15000.0

            if (area_ratio >= min_expansion_ratio or expansion_rate >= min_expansion_rate_px) and is_foreground:
                conf = min(0.95, round(0.55 + min(0.40, (area_ratio - 1.0) * 0.3), 2))
                events.append(
                    VideoEvent(
                        video_id=curr.video_id,
                        camera_id=camera_id,
                        event_type="REVIEW_FLAG_EGO_COLLISION_WARNING",
                        start_time=prev.timestamp,
                        end_time=curr.timestamp,
                        confidence=conf,
                        track_id=track_id,
                        object_type=curr.object_type,
                        metadata={
                            "reason": "rapid_looming_approach",
                            "area_growth_ratio": round(area_ratio, 2),
                            "expansion_rate_px_per_sec": round(expansion_rate, 1),
                            "bbox": curr.bbox,
                            "note": (
                                "Flagged for human review. Rapid optical expansion and close "
                                "foreground proximity detected between the camera vehicle and this tracked vehicle."
                            ),
                        },
                    )
                )
                break  # Flag primary looming incident once per track

    return events


def detect_sudden_stop_events(
    detections: list[Detection],
    min_points: int = 2,
    speed_drop_ratio: float = 0.50,
    moving_speed_floor: float = 3.0,
) -> list[VideoEvent]:
    """Flag a single track whose frame-to-frame speed drops sharply after
    having established it was moving. A candidate for sudden stop or impact deceleration.
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
                continue

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
                                "obstruction, or impact collision."
                            ),
                        },
                    )
                )

    return events


def detect_incident_candidates(detections: list[Detection]) -> list[VideoEvent]:
    """Convenience wrapper combining inter-vehicle proximity/contact, dashcam looming crash candidates, and sudden stops."""
    return (
        detect_proximity_events(detections)
        + detect_ego_collision_events(detections)
        + detect_sudden_stop_events(detections)
    )