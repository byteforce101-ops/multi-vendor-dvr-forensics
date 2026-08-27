from __future__ import annotations

from datetime import datetime, timedelta, timezone


def ensure_timezone(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)

    return value


def frame_to_absolute_timestamp(
    video_start: datetime,
    relative_seconds: float,
) -> datetime:
    """
    Convert a decoded video's relative timestamp into
    the absolute forensic/CCTV timestamp.

    The start timestamp must come from the parser/probe whenever
    available.
    """

    start = ensure_timezone(video_start)

    return start + timedelta(
        seconds=max(0.0, relative_seconds)
    )


def normalize_timestamp(
    timestamp: datetime,
    offset_seconds: float = 0.0,
) -> datetime:
    """
    Apply a documented clock correction.

    Example:
    DVR clock was 2 minutes slow:
        offset_seconds = 120
    """

    timestamp = ensure_timezone(timestamp)

    return timestamp + timedelta(
        seconds=offset_seconds
    )