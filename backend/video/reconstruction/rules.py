from __future__ import annotations

from datetime import timedelta

from backend.video.analysis.models import VideoEvent

from backend.video.reconstruction.models import (
    ForensicEvidence,
    ReconstructedEvent,
)


def _confidence(events: list[VideoEvent]) -> float:
    values = [
        event.confidence
        for event in events
        if event.confidence is not None
    ]

    if not values:
        return 0.0

    return max(values)


def _objects(events: list[VideoEvent]) -> list[str]:
    return sorted(
        {
            event.object_type
            for event in events
            if event.object_type
        }
    )


def _evidence(
    events: list[VideoEvent],
) -> list[ForensicEvidence]:

    result = []

    for event in events:

        result.append(
            ForensicEvidence(
                event_type=event.event_type,
                timestamp=event.start_time,
                object_type=event.object_type,
                confidence=event.confidence,
                track_id=event.track_id,
                metadata=event.metadata,
            )
        )

    return result


def reconstruct_activity(
    events: list[VideoEvent],
) -> ReconstructedEvent | None:

    if not events:
        return None

    first = events[0]

    objects = _objects(events)

    event_types = {
        event.event_type
        for event in events
    }

    # ---------------------------------------------------------
    # VEHICLE / COLLISION
    # ---------------------------------------------------------

    vehicles = {
        "car",
        "truck",
        "bus",
        "motorcycle",
        "bicycle",
    }

    detected_vehicles = [
        event
        for event in events
        if event.object_type in vehicles
    ]

    if len(detected_vehicles) >= 2:

        return ReconstructedEvent(
            video_id=first.video_id,
            camera_id=first.camera_id,
            event_type="POSSIBLE_VEHICLE_INTERACTION",
            start_time=min(
                event.start_time
                for event in events
            ),
            end_time=max(
                event.end_time
                for event in events
            ),
            title="Possible vehicle interaction",
            description=(
                "Multiple vehicles were detected "
                "within the same activity window. "
                "The available detections support "
                "a possible vehicle interaction, "
                "but do not by themselves establish "
                "a collision."
            ),
            objects=objects,
            confidence=_confidence(events),
            evidence=_evidence(events),
            metadata={
                "rule": "multiple_vehicles",
            },
        )

    # ---------------------------------------------------------
    # PERSON + VEHICLE
    # ---------------------------------------------------------

    people = any(
        event.object_type == "person"
        for event in events
    )

    vehicle = any(
        event.object_type in vehicles
        for event in events
    )

    if people and vehicle:

        return ReconstructedEvent(
            video_id=first.video_id,
            camera_id=first.camera_id,
            event_type="PERSON_VEHICLE_ACTIVITY",
            start_time=min(
                event.start_time
                for event in events
            ),
            end_time=max(
                event.end_time
                for event in events
            ),
            title="Person and vehicle activity",
            description=(
                "A person and a vehicle were detected "
                "during the same activity window."
            ),
            objects=objects,
            confidence=_confidence(events),
            evidence=_evidence(events),
            metadata={
                "rule": "person_vehicle",
            },
        )

    # ---------------------------------------------------------
    # PERSON + OBJECT
    # ---------------------------------------------------------

    if people and len(objects) >= 2:

        non_people = [
            obj
            for obj in objects
            if obj != "person"
        ]

        return ReconstructedEvent(
            video_id=first.video_id,
            camera_id=first.camera_id,
            event_type="PERSON_OBJECT_ACTIVITY",
            start_time=min(
                event.start_time
                for event in events
            ),
            end_time=max(
                event.end_time
                for event in events
            ),
            title="Person and object activity",
            description=(
                "A person was detected during a "
                "period in which the following objects "
                f"were also visible: "
                f"{', '.join(non_people)}."
            ),
            objects=objects,
            confidence=_confidence(events),
            evidence=_evidence(events),
            metadata={
                "rule": "person_object",
            },
        )

    # ---------------------------------------------------------
    # MOTION
    # ---------------------------------------------------------

    if "MOTION" in event_types:

        return ReconstructedEvent(
            video_id=first.video_id,
            camera_id=first.camera_id,
            event_type="MOTION_ACTIVITY",
            start_time=min(
                event.start_time
                for event in events
            ),
            end_time=max(
                event.end_time
                for event in events
            ),
            title="Motion activity detected",
            description=(
                "Significant visual movement was "
                "detected in the camera scene."
            ),
            objects=objects,
            confidence=_confidence(events),
            evidence=_evidence(events),
            metadata={
                "rule": "motion",
            },
        )

    # ---------------------------------------------------------
    # GENERIC ACTIVITY
    # ---------------------------------------------------------

    return ReconstructedEvent(
        video_id=first.video_id,
        camera_id=first.camera_id,
        event_type="GENERAL_ACTIVITY",
        start_time=min(
            event.start_time
            for event in events
        ),
        end_time=max(
            event.end_time
            for event in events
        ),
        title="Detected activity",
        description=(
            "Objects or activity were detected "
            "within the analysed video."
        ),
        objects=objects,
        confidence=_confidence(events),
        evidence=_evidence(events),
        metadata={
            "rule": "generic",
        },
    )