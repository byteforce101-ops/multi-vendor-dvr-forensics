from __future__ import annotations

from datetime import timedelta

from backend.video.analysis.models import VideoEvent

from backend.video.reconstruction.models import (
    ForensicEvidence,
    ReconstructedEvent,
)


# =========================================================
# RECONSTRUCTION THRESHOLDS
# =========================================================

# Two vehicle detections must occur within this time window
# before we even consider a possible interaction.
VEHICLE_INTERACTION_WINDOW_SECONDS = 1.5

# Require reasonably strong detections before creating a
# possible vehicle interaction.
VEHICLE_INTERACTION_CONFIDENCE = 0.60


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


def _vehicle_events(
    events: list[VideoEvent],
) -> list[VideoEvent]:

    vehicles = {
        "car",
        "truck",
        "bus",
        "motorcycle",
        "bicycle",
    }

    return [
        event
        for event in events
        if event.object_type in vehicles
    ]


def _supports_vehicle_interaction(
    events: list[VideoEvent],
) -> bool:
    """
    Determine whether the available event-level evidence
    is strong enough to support a possible vehicle
    interaction.

    Important:
    This function does NOT establish a collision.

    It only looks for:
      1. At least two vehicle detections.
      2. Reasonably strong confidence.
      3. Very close temporal proximity.

    Spatial interaction cannot currently be evaluated
    because VideoEvent does not contain bounding boxes.
    """

    vehicle_events = _vehicle_events(events)

    if len(vehicle_events) < 2:
        return False

    strong_vehicle_events = [
        event
        for event in vehicle_events
        if (
            event.confidence is not None
            and event.confidence >= VEHICLE_INTERACTION_CONFIDENCE
        )
    ]

    if len(strong_vehicle_events) < 2:
        return False

    for index, first in enumerate(strong_vehicle_events):

        for second in strong_vehicle_events[index + 1:]:

            first_end = first.end_time
            second_start = second.start_time

            second_end = second.end_time
            first_start = first.start_time

            # Calculate the temporal distance between the
            # two activity intervals.
            if first_end < second_start:
                gap = (
                    second_start - first_end
                ).total_seconds()

            elif second_end < first_start:
                gap = (
                    first_start - second_end
                ).total_seconds()

            else:
                # Intervals overlap.
                gap = 0.0

            if gap <= VEHICLE_INTERACTION_WINDOW_SECONDS:
                return True

    return False


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

    # =========================================================
    # VEHICLE / POSSIBLE INTERACTION
    # =========================================================

    if _supports_vehicle_interaction(events):

        vehicle_events = _vehicle_events(events)

        return ReconstructedEvent(
            video_id=first.video_id,
            camera_id=first.camera_id,
            event_type="POSSIBLE_VEHICLE_INTERACTION",
            start_time=min(
                event.start_time
                for event in vehicle_events
            ),
            end_time=max(
                event.end_time
                for event in vehicle_events
            ),
            title="Possible vehicle interaction",
            description=(
                "Two or more vehicles were detected "
                "with reasonably strong confidence and "
                "within a short temporal interval. "
                "This supports a possible vehicle "
                "interaction, but the available evidence "
                "does not establish physical contact or "
                "a collision."
            ),
            objects=objects,
            confidence=_confidence(
                vehicle_events
            ),
            evidence=_evidence(
                vehicle_events
            ),
            metadata={
                "rule": "vehicle_temporal_proximity",
                "temporal_window_seconds": (
                    VEHICLE_INTERACTION_WINDOW_SECONDS
                ),
                "minimum_confidence": (
                    VEHICLE_INTERACTION_CONFIDENCE
                ),
                "spatial_relationship_verified": False,
            },
        )

    # =========================================================
    # PERSON + VEHICLE
    # =========================================================

    people = any(
        event.object_type == "person"
        for event in events
    )

    vehicle = any(
        event.object_type
        in {
            "car",
            "truck",
            "bus",
            "motorcycle",
            "bicycle",
        }
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

    # =========================================================
    # PERSON + OBJECT
    # =========================================================

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

    # =========================================================
    # MOTION
    # =========================================================

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

    # =========================================================
    # GENERIC ACTIVITY
    # =========================================================

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