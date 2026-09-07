"""backend/tests/test_forensic_event_summarizer.py — Tests for forensic event filtering and activity digest summarization."""

from datetime import datetime, timezone, timedelta
import pytest

from backend.video.analysis.models import Detection, VideoEvent
from backend.ai.events.event_builder import (
    build_detection_events,
    generate_forensic_activity_digest,
    format_forensic_activity_digest_markdown,
)


def test_build_detection_events_filters_single_frame_noise():
    """Verify that min_observations=2 filters out 1-frame transient spikes."""
    t0 = datetime(2026, 9, 6, 12, 0, 0, tzinfo=timezone.utc)

    # 1 transient blip (only 1 observation)
    transient_det = Detection(
        video_id="cam1",
        camera_id="cam_01",
        frame_number=1,
        timestamp=t0,
        object_type="person",
        confidence=0.6,
        bbox=(10, 10, 30, 60),
        track_id=1,
    )

    # 1 real persistent object (3 observations over 2 seconds)
    persistent_dets = [
        Detection(
            video_id="cam1",
            camera_id="cam_01",
            frame_number=10,
            timestamp=t0 + timedelta(seconds=10),
            object_type="vehicle",
            confidence=0.85,
            bbox=(100, 100, 200, 160),
            track_id=2,
        ),
        Detection(
            video_id="cam1",
            camera_id="cam_01",
            frame_number=12,
            timestamp=t0 + timedelta(seconds=11),
            object_type="vehicle",
            confidence=0.87,
            bbox=(120, 100, 220, 160),
            track_id=2,
        ),
        Detection(
            video_id="cam1",
            camera_id="cam_01",
            frame_number=14,
            timestamp=t0 + timedelta(seconds=12),
            object_type="vehicle",
            confidence=0.89,
            bbox=(140, 100, 240, 160),
            track_id=2,
        ),
    ]

    all_dets = [transient_det] + persistent_dets

    # Without pruning (min_observations=1) -> 2 events
    events_raw = build_detection_events(all_dets, min_observations=1)
    assert len(events_raw) == 2

    # With pruning (min_observations=2, min_duration_seconds=1.0) -> only the persistent vehicle
    events_pruned = build_detection_events(all_dets, min_observations=2, min_duration_seconds=1.0)
    assert len(events_pruned) == 1
    assert events_pruned[0].object_type == "vehicle"
    assert events_pruned[0].track_id == 2


def test_generate_forensic_activity_digest():
    """Verify executive summary aggregation with entities, loitering, and movements."""
    t0 = datetime(2026, 9, 6, 14, 30, 0, tzinfo=timezone.utc)

    # Create synthetic events: 1 loitering person, 1 moving car, 1 review flag
    ev_person = VideoEvent(
        video_id="v1",
        camera_id="cam_entrance",
        event_type="PERSON_DETECTED",
        start_time=t0,
        end_time=t0 + timedelta(seconds=8),
        confidence=0.85,
        track_id=101,
        object_type="person",
        metadata={
            "entity_id": "person#101",
            "is_loitering": True,
            "direction": "Stationary",
            "avg_speed": 1.2,
        },
    )

    ev_vehicle = VideoEvent(
        video_id="v1",
        camera_id="cam_entrance",
        event_type="VEHICLE_DETECTED",
        start_time=t0 + timedelta(seconds=5),
        end_time=t0 + timedelta(seconds=15),
        confidence=0.92,
        track_id=202,
        object_type="vehicle",
        metadata={
            "entity_id": "vehicle#202",
            "is_loitering": False,
            "direction": "Eastbound (→)",
            "avg_speed": 45.0,
        },
    )

    ev_flag = VideoEvent(
        video_id="v1",
        camera_id="cam_entrance",
        event_type="REVIEW_FLAG_PROXIMITY",
        start_time=t0 + timedelta(seconds=6),
        end_time=t0 + timedelta(seconds=6),
        confidence=0.78,
        metadata={
            "reason": "bounding_box_overlap",
        },
    )

    events = [ev_person, ev_vehicle, ev_flag]
    digest = generate_forensic_activity_digest(events, suppressed_noise_count=14)

    assert digest["total_events"] == 3
    assert digest["unique_entities"]["person"] == 1
    assert digest["unique_entities"]["vehicle"] == 1
    assert len(digest["loitering_events"]) == 1
    assert digest["loitering_events"][0]["entity_id"] == "person#101"
    assert len(digest["movement_highlights"]) == 1
    assert digest["movement_highlights"][0]["entity_id"] == "vehicle#202"
    assert len(digest["review_flags"]) == 1
    assert digest["suppressed_noise_count"] == 14

    md = digest["markdown_summary"]
    assert "Forensic Activity Digest" in md
    assert "1 Person" in md
    assert "1 Vehicle" in md
    assert "Loitering" in md
    assert "Eastbound" in md
    assert "REVIEW_FLAG_PROXIMITY" in md
    assert "14 transient blips suppressed" in md
