from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class ForensicEvidence:
    """
    Raw evidence supporting a reconstructed activity.
    """

    event_type: str
    timestamp: datetime
    object_type: str | None = None
    confidence: float | None = None
    track_id: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ReconstructedEvent:
    """
    Higher-level activity reconstructed from one or more
    low-level forensic events.
    """

    video_id: str
    camera_id: str

    event_type: str

    start_time: datetime
    end_time: datetime

    title: str
    description: str

    objects: list[str] = field(default_factory=list)

    confidence: float = 0.0

    evidence: list[ForensicEvidence] = field(
        default_factory=list
    )

    metadata: dict[str, Any] = field(
        default_factory=dict
    )


@dataclass
class ForensicSummary:
    """
    Final investigator-facing summary of the analysed video.
    """

    video_id: str
    camera_id: str

    start_time: datetime | None
    end_time: datetime | None

    headline: str

    summary: str

    key_events: list[str] = field(
        default_factory=list
    )

    objects_detected: list[str] = field(
        default_factory=list
    )

    event_count: int = 0

    confidence: float = 0.0

    metadata: dict[str, Any] = field(
        default_factory=dict
    )