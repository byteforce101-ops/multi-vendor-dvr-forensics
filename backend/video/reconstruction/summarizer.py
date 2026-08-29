from __future__ import annotations

from backend.video.reconstruction.models import (
    ForensicSummary,
    ReconstructedEvent,
)


def _confidence_label(
    confidence: float,
) -> str:

    if confidence >= 0.80:
        return "HIGH"

    if confidence >= 0.60:
        return "MEDIUM"

    if confidence >= 0.35:
        return "LOW"

    return "VERY LOW"


def build_forensic_summary(
    video_id: str,
    camera_id: str,
    events: list[ReconstructedEvent],
) -> ForensicSummary:

    if not events:

        return ForensicSummary(
            video_id=video_id,
            camera_id=camera_id,
            start_time=None,
            end_time=None,
            headline="No significant activity detected",
            summary=(
                "No reconstructable activity was "
                "identified from the available "
                "motion and object detections."
            ),
            key_events=[],
            objects_detected=[],
            event_count=0,
            confidence=0.0,
        )

    ordered = sorted(
        events,
        key=lambda event: event.start_time,
    )

    objects = sorted(
        {
            obj
            for event in ordered
            for obj in event.objects
        }
    )

    confidence = max(
        event.confidence
        for event in ordered
    )

    key_events = []

    for event in ordered:

        key_events.append(
            f"{event.start_time} - "
            f"{event.title}"
        )

    # ---------------------------------------------------------
    # PRIORITIZE IMPORTANT INCIDENT TYPES
    # ---------------------------------------------------------

    vehicle_events = [
        event
        for event in ordered
        if event.event_type
        == "POSSIBLE_VEHICLE_INTERACTION"
    ]

    if vehicle_events:

        headline = (
            "Possible vehicle interaction detected"
        )

        summary = (
            "The video contains activity involving "
            "multiple detected vehicles. The "
            "available computer-vision evidence "
            "supports a possible vehicle interaction "
            "during the analysed period. A collision "
            "cannot be confirmed solely from these "
            "detections."
        )

    elif any(
        event.event_type
        == "PERSON_VEHICLE_ACTIVITY"
        for event in ordered
    ):

        headline = (
            "Person and vehicle activity detected"
        )

        summary = (
            "The video shows a period in which a "
            "person and a vehicle were detected in "
            "the same activity window."
        )

    elif any(
        event.event_type
        == "PERSON_OBJECT_ACTIVITY"
        for event in ordered
    ):

        headline = (
            "Person and object activity detected"
        )

        summary = (
            "The video shows a person present during "
            "a period in which multiple objects were "
            "also detected."
        )

    elif any(
        event.event_type
        == "MOTION_ACTIVITY"
        for event in ordered
    ):

        headline = (
            "Significant scene activity detected"
        )

        summary = (
            "The video contains significant visual "
            "movement and detected object activity."
        )

    else:

        headline = "Detected activity in video"

        summary = (
            "The analysis identified objects or "
            "activity within the video. The detected "
            "evidence is summarized in the event "
            "timeline below."
        )

    confidence_label = _confidence_label(
        confidence
    )

    summary = (
        f"{summary} Overall reconstruction "
        f"confidence: {confidence_label}."
    )

    return ForensicSummary(
        video_id=video_id,
        camera_id=camera_id,
        start_time=ordered[0].start_time,
        end_time=ordered[-1].end_time,
        headline=headline,
        summary=summary,
        key_events=key_events,
        objects_detected=objects,
        event_count=len(ordered),
        confidence=confidence,
        metadata={
            "confidence_label": confidence_label,
        },
    )