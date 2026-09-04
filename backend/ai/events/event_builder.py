from __future__ import annotations

from collections import defaultdict

from backend.video.analysis.models import (
    Detection,
    VideoEvent,
)


def build_detection_events(
    detections: list[Detection],
    max_gap_seconds: float = 3.0,
) -> list[VideoEvent]:

    grouped: dict[
        tuple[str, int | None, str],
        list[Detection],
    ] = defaultdict(list)

    # =========================================================
    # GROUP BY INDIVIDUAL OBJECT
    # =========================================================

    for detection in detections:

        key = (
            detection.object_type,
            detection.track_id,
            detection.camera_id,
        )

        grouped[key].append(
            detection
        )

    events: list[VideoEvent] = []

    # =========================================================
    # BUILD OBJECT-SPECIFIC EVENTS
    # =========================================================

    for (
        object_type,
        track_id,
        camera_id,
    ), group in grouped.items():

        group.sort(
            key=lambda item: item.timestamp
        )

        current: list[Detection] = [
            group[0]
        ]

        for detection in group[1:]:

            previous = current[-1]

            gap = (
                detection.timestamp
                - previous.timestamp
            ).total_seconds()

            if gap <= max_gap_seconds:

                current.append(
                    detection
                )

                continue

            events.append(
                _make_event(
                    current,
                    object_type,
                    track_id,
                    camera_id,
                )
            )

            current = [
                detection
            ]

        if current:

            events.append(
                _make_event(
                    current,
                    object_type,
                    track_id,
                    camera_id,
                )
            )

    return sorted(
        events,
        key=lambda event: event.start_time,
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


def _make_event(
    detections: list[Detection],
    object_type: str,
    track_id: int | None,
    camera_id: str,
) -> VideoEvent:

    # =========================================================
    # PRESERVE EVERY OBSERVATION & EXTRACT KINEMATICS
    # =========================================================

    observations = []
    centroids = []
    speeds = []

    for idx, detection in enumerate(detections):
        bx = detection.bbox
        cx = (bx[0] + bx[2]) / 2.0
        cy = (bx[1] + bx[3]) / 2.0
        centroids.append((cx, cy))

        vel = detection.metadata.get("velocity", (0.0, 0.0)) if isinstance(detection.metadata, dict) else (0.0, 0.0)
        if math.hypot(vel[0], vel[1]) < 0.1 and idx > 0:
            prev_cx, prev_cy = centroids[idx - 1]
            dt_s = max(0.05, (detection.timestamp - detections[idx - 1].timestamp).total_seconds())
            vel = ((cx - prev_cx) / dt_s, (cy - prev_cy) / dt_s)

        v_speed = math.hypot(vel[0], vel[1])
        if v_speed > 0.0:
            speeds.append(v_speed)

        observations.append(
            {
                "frame_number": (
                    detection.frame_number
                ),
                "timestamp": (
                    detection.timestamp.isoformat()
                ),
                "confidence": (
                    detection.confidence
                ),
                "bbox": [
                    float(value)
                    for value in detection.bbox
                ],
                "velocity": [float(vel[0]), float(vel[1])],
            }
        )

    # Trajectory & kinematics
    start_pt = centroids[0]
    end_pt = centroids[-1]
    displacement = math.hypot(end_pt[0] - start_pt[0], end_pt[1] - start_pt[1])
    dur = max(0.1, (detections[-1].timestamp - detections[0].timestamp).total_seconds())
    disp_speed = displacement / dur if dur > 0 else 0.0
    avg_speed = max(disp_speed, (sum(speeds) / len(speeds)) if speeds else 0.0)
    overall_vx = (end_pt[0] - start_pt[0]) / dur
    overall_vy = (end_pt[1] - start_pt[1]) / dur
    direction = _direction_from_vector(overall_vx, overall_vy) if (displacement >= 15.0 or avg_speed >= 5.0) else "Stationary"
    is_loitering = (dur >= 3.0 and displacement <= 60.0 and object_type in ("person", "vehicle", "car"))

    # =========================================================
    # ENTITY ID
    # =========================================================

    if track_id is not None:

        entity_id = (
            f"{object_type}#{track_id}"
        )

    else:

        entity_id = object_type

    # =========================================================
    # EVENT
    # =========================================================

    return VideoEvent(
        video_id=detections[0].video_id,
        camera_id=camera_id,

        event_type=(
            f"{object_type.upper()}_DETECTED"
        ),

        start_time=(
            detections[0].timestamp
        ),

        end_time=(
            detections[-1].timestamp
        ),

        confidence=max(
            detection.confidence
            for detection in detections
        ),

        track_id=track_id,

        object_type=object_type,

        metadata={
            "entity_id": entity_id,

            "detection_count": (
                len(detections)
            ),

            "first_frame": (
                detections[0].frame_number
            ),

            "last_frame": (
                detections[-1].frame_number
            ),

            "first_seen": (
                detections[0]
                .timestamp
                .isoformat()
            ),

            "last_seen": (
                detections[-1]
                .timestamp
                .isoformat()
            ),

            "displacement": displacement,
            "avg_speed": avg_speed,
            "direction": direction,
            "is_loitering": is_loitering,

            "observations": observations,

            "source": (
                detections[0]
                .metadata
                .get("source", "yolo")
                if isinstance(detections[0].metadata, dict)
                else "yolo"
            ),

            "verified": any(
                detection.metadata.get(
                    "verified",
                    False,
                )
                for detection in detections
                if isinstance(detection.metadata, dict)
            ),
        },
    )