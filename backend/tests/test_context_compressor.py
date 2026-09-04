"""Unit tests for context compression and query-aware RAG filtering."""

from datetime import datetime, timezone, timedelta
from backend.core.search.context_compressor import (
    compress_events_into_track_spans,
    build_compact_forensic_context,
)
from backend.video.analysis.models import VideoEvent
from backend.video.reconstruction.models import ReconstructedEvent, ForensicSummary


def test_compress_events_into_track_spans():
    base_time = datetime(2026, 9, 4, 12, 0, 0, tzinfo=timezone.utc)
    raw_events = []

    # 100 raw per-frame detections for track 1 (Person)
    for i in range(100):
        t = base_time + timedelta(seconds=i * 0.5)
        raw_events.append(
            VideoEvent(
                video_id="v1",
                camera_id="CH-01",
                event_type="PERSON_DETECTED",
                object_type="person",
                start_time=t,
                end_time=t + timedelta(seconds=0.5),
                confidence=0.88,
                track_id=1,
                metadata={"direction": "Eastbound (->)", "avg_speed": 12.5, "is_loitering": False},
            )
        )

    # 50 raw per-frame detections for track 2 (Vehicle)
    for i in range(50):
        t = base_time + timedelta(seconds=i * 0.5)
        raw_events.append(
            VideoEvent(
                video_id="v1",
                camera_id="CH-01",
                event_type="VEHICLE_DETECTED",
                object_type="vehicle",
                start_time=t,
                end_time=t + timedelta(seconds=0.5),
                confidence=0.92,
                track_id=2,
                metadata={"direction": "Northbound (^)", "avg_speed": 24.0, "is_loitering": True},
            )
        )

    spans = compress_events_into_track_spans(raw_events)

    # Should compress 150 events down to exactly 2 track spans
    assert len(spans) == 2

    span_person = next(s for s in spans if s.object_type == "person")
    assert span_person.observation_count == 100
    assert span_person.duration_seconds >= 49.0
    assert span_person.direction == "Eastbound (->)"

    span_veh = next(s for s in spans if s.object_type == "vehicle")
    assert span_veh.observation_count == 50
    assert span_veh.is_loitering is True


def test_build_compact_forensic_context_budget_and_relevance():
    base_time = datetime(2026, 9, 4, 12, 0, 0, tzinfo=timezone.utc)

    # Generate 500 synthetic events
    raw_events = [
        VideoEvent(
            video_id="v1",
            camera_id="CH-01",
            event_type="MOTION",
            object_type="object",
            start_time=base_time + timedelta(seconds=i * 0.2),
            end_time=base_time + timedelta(seconds=(i + 1) * 0.2),
            confidence=0.75,
            track_id=i % 10,
        )
        for i in range(500)
    ]

    reconstructed_events = [
        ReconstructedEvent(
            video_id="v1",
            camera_id="CH-01",
            event_type="LOITERING_DETECTED",
            start_time=base_time,
            end_time=base_time + timedelta(seconds=10),
            title="Suspicious Loitering: Person #3",
            description="Person remained stationary for 10 seconds near entrance.",
            confidence=0.90,
        ),
        ReconstructedEvent(
            video_id="v1",
            camera_id="CH-01",
            event_type="VEHICLE_TRACK",
            start_time=base_time + timedelta(seconds=15),
            end_time=base_time + timedelta(seconds=25),
            title="Vehicle #5 Active in Scene",
            description="Vehicle moved Northbound at 30 px/s.",
            confidence=0.85,
        ),
    ]

    summaries = [
        ForensicSummary(
            video_id="v1",
            camera_id="CH-01",
            start_time=base_time,
            end_time=base_time + timedelta(seconds=100),
            headline="Surveillance Scene: 1 Person, 1 Vehicle",
            summary="OpenCV forensic reconstruction tracked 2 active entities.",
            key_events=["Person loitered for 10s", "Vehicle transited Northbound"],
        )
    ]

    # Test query-aware context generation
    context = build_compact_forensic_context(
        video_name="test_surveillance.dd",
        raw_events=raw_events,
        reconstructed_events=reconstructed_events,
        forensic_summaries=summaries,
        query="was there any suspicious loitering?",
    )

    # Verify context is compact (< 3,500 characters)
    assert len(context) < 3500
    assert "Suspicious Loitering" in context
    assert "LOITERING_DETECTED" in context
    assert "condensed into" in context
