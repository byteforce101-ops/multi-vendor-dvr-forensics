from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class Detection:
    video_id: str
    camera_id: str
    frame_number: int
    timestamp: datetime
    object_type: str
    confidence: float
    bbox: tuple[float, float, float, float]
    track_id: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class VideoEvent:
    video_id: str
    camera_id: str
    event_type: str
    start_time: datetime
    end_time: datetime
    confidence: float | None = None
    track_id: int | None = None
    object_type: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)