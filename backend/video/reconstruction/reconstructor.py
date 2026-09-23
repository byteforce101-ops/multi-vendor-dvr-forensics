from __future__ import annotations

from datetime import timedelta

from backend.video.analysis.models import VideoEvent

from backend.video.reconstruction.models import (
    ReconstructedEvent,
)

from backend.video.reconstruction.rules import (
    reconstruct_activity,
)


DEFAULT_ACTIVITY_GAP_SECONDS = 1.5


def reconstruct_events(
    events: list[VideoEvent],
    max_gap_seconds: float = DEFAULT_ACTIVITY_GAP_SECONDS,
) -> list[ReconstructedEvent]:

    if not events:
        return []

    ordered = sorted(
        events,
        key=lambda event: event.start_time,
    )

    groups: list[list[VideoEvent]] = []

    current: list[VideoEvent] = [
        ordered[0]
    ]

    for event in ordered[1:]:

        previous = current[-1]

        gap = (
            event.start_time
            - previous.end_time
        ).total_seconds()

        if gap <= max_gap_seconds and len(current) < 3:

            current.append(event)

        else:

            groups.append(current)

            current = [event]

    if current:
        groups.append(current)

    reconstructed: list[
        ReconstructedEvent
    ] = []

    for idx, group in enumerate(groups, start=1):

        event = reconstruct_activity(group)

        if event is not None:
            if len(groups) > 1:
                event.title = f"{event.title} (Phase {idx})"
            reconstructed.append(event)

    return sorted(
        reconstructed,
        key=lambda event: event.start_time,
    )