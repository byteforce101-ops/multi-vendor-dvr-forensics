from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from backend.video.analysis.models import VideoEvent


@dataclass(frozen=True)
class TimelineItem:
    timestamp: datetime
    end_timestamp: datetime
    camera_id: str
    event_type: str
    video_id: str
    confidence: float | None
    object_type: str | None
    track_id: int | None


def build_timeline(
    events: list[VideoEvent],
) -> list[TimelineItem]:

    return [
        TimelineItem(
            timestamp=event.start_time,
            end_timestamp=event.end_time,
            camera_id=event.camera_id,
            event_type=event.event_type,
            video_id=event.video_id,
            confidence=event.confidence,
            object_type=event.object_type,
            track_id=event.track_id,
        )
        for event in sorted(
            events,
            key=lambda event: event.start_time,
        )
    ]


def filter_timeline(
    events: list[VideoEvent],
    start: datetime | None = None,
    end: datetime | None = None,
    camera_id: str | None = None,
    event_type: str | None = None,
) -> list[VideoEvent]:

    result = events

    if start is not None:
        result = [
            event
            for event in result
            if event.end_time >= start
        ]

    if end is not None:
        result = [
            event
            for event in result
            if event.start_time <= end
        ]

    if camera_id is not None:
        result = [
            event
            for event in result
            if event.camera_id == camera_id
        ]

    if event_type is not None:
        result = [
            event
            for event in result
            if event.event_type == event_type
        ]

    return sorted(
        result,
        key=lambda event: event.start_time,
    )