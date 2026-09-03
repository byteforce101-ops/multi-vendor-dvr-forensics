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


def _make_event(
    detections: list[Detection],
    object_type: str,
    track_id: int | None,
    camera_id: str,
) -> VideoEvent:

    # =========================================================
    # PRESERVE EVERY OBSERVATION
    # =========================================================

    observations = []

    for detection in detections:

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
            }
        )

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

            "observations": observations,

            "source": (
                detections[0]
                .metadata
                .get("source", "yolo")
            ),

            "verified": any(
                detection.metadata.get(
                    "verified",
                    False,
                )
                for detection in detections
            ),
        },
    )