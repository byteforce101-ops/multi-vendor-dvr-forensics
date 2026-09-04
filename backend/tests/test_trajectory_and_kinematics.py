"""Unit tests for trajectory tracking, velocity propagation, and LLM context formatting."""

from datetime import datetime, timezone, timedelta
import numpy as np
import pytest

from backend.ai.detectors.opencv_forensic_detector import (
    OpenCVForensicDetector,
    OpenCVForensicDetection,
)
from backend.video.reconstruction.opencv_reconstructor import (
    OpenCVForensicReconstructor,
    _direction_from_vector,
)
from backend.video.analysis.models import Detection, VideoEvent
from backend.ai.events.event_builder import build_detection_events
from backend.core.search.context_compressor import (
    compress_events_into_track_spans,
    build_compact_forensic_context,
)


def test_direction_from_vector():
    """Verify 8-point compass directions from velocity vectors."""
    assert _direction_from_vector(0.0, 0.0) == "Stationary"
    assert _direction_from_vector(2.0, 1.0) == "Stationary"  # below 5 px/s threshold
    assert _direction_from_vector(50.0, 0.0) == "Eastbound (→)"
    assert _direction_from_vector(-50.0, 0.0) == "Westbound (←)"
    assert _direction_from_vector(0.0, 50.0) == "Southbound (↓)"
    assert _direction_from_vector(0.0, -50.0) == "Northbound (↑)"
    assert _direction_from_vector(50.0, 50.0) == "South-East (↘)"
    assert _direction_from_vector(-50.0, 50.0) == "South-West (↙)"
    assert _direction_from_vector(-50.0, -50.0) == "North-West (↖)"
    assert _direction_from_vector(50.0, -50.0) == "North-East (↗)"


def test_opencv_tracker_moving_vehicle():
    """Verify OpenCVForensicDetector tracks moving vehicle across frames and estimates velocity."""
    detector = OpenCVForensicDetector()
    detector.reset_tracks()

    # Frame 1: Vehicle at (100, 200, 300, 300) -> center (200, 250)
    det1 = OpenCVForensicDetection(
        class_name="vehicle",
        confidence=0.85,
        bbox=(100.0, 200.0, 300.0, 300.0),
    )
    res1 = detector._update_tracks([det1], fps=2.0)
    assert len(res1) == 1
    t_id = res1[0].track_id
    assert t_id is not None
    assert res1[0].velocity == (0.0, 0.0)

    # Frame 2 (0.5s later): Vehicle moved right by 100px -> center (300, 250)
    det2 = OpenCVForensicDetection(
        class_name="vehicle",
        confidence=0.88,
        bbox=(200.0, 200.0, 400.0, 300.0),
    )
    res2 = detector._update_tracks([det2], fps=2.0)
    assert len(res2) == 1
    assert res2[0].track_id == t_id  # Track ID must be preserved
    vx, vy = res2[0].velocity
    assert vx > 150.0  # ~200 px/s (100px in 0.5s)
    assert abs(vy) < 1.0


def test_reconstructor_velocity_and_heading():
    """Verify OpenCVForensicReconstructor calculates speed and direction from tracked detections."""
    reconstructor = OpenCVForensicReconstructor()
    base_time = datetime(2026, 9, 4, 12, 0, 0, tzinfo=timezone.utc)

    # Simulate 3 observations of a moving car moving Eastbound
    class MockDet:
        def __init__(self, fn, ts, bbox, vel, obj_type="vehicle", track_id=101):
            self.frame_number = fn
            self.timestamp_seconds = ts
            self.bbox = bbox
            self.velocity = vel
            self.object_type = obj_type
            self.track_id = track_id
            self.confidence = 0.90

    dets = [
        (0.0, [MockDet(0, 0.0, (100.0, 200.0, 300.0, 300.0), (0.0, 0.0))]),
        (0.5, [MockDet(1, 0.5, (200.0, 200.0, 400.0, 300.0), (200.0, 0.0))]),
        (1.0, [MockDet(2, 1.0, (300.0, 200.0, 500.0, 300.0), (200.0, 0.0))]),
    ]

    events, summary = reconstructor.reconstruct_from_detections(
        dets,
        video_start_time=base_time,
        video_id="test_vid",
        camera_id="CH-01",
    )

    assert len(events) >= 1
    track_event = next(e for e in events if e.event_type == "VEHICLE_TRACK")
    assert track_event.metadata["track_id"] == 101
    assert "Eastbound" in track_event.metadata["direction"]
    assert track_event.metadata["avg_speed"] >= 150.0
    assert track_event.metadata["displacement"] >= 180.0
    assert "Eastbound" in track_event.description


def test_event_builder_and_context_compressor():
    """Verify build_detection_events stores kinematics and context_compressor outputs non-stationary speed."""
    base_time = datetime(2026, 9, 4, 12, 0, 0, tzinfo=timezone.utc)

    detections = [
        Detection(
            video_id="vid1",
            camera_id="CH-01",
            frame_number=0,
            timestamp=base_time,
            object_type="vehicle",
            confidence=0.85,
            bbox=(100.0, 200.0, 300.0, 300.0),
            track_id=42,
            metadata={"source": "opencv", "velocity": (0.0, 0.0)},
        ),
        Detection(
            video_id="vid1",
            camera_id="CH-01",
            frame_number=1,
            timestamp=base_time + timedelta(seconds=0.5),
            object_type="vehicle",
            confidence=0.90,
            bbox=(250.0, 200.0, 450.0, 300.0),
            track_id=42,
            metadata={"source": "opencv", "velocity": (300.0, 0.0)},
        ),
    ]

    events = build_detection_events(detections)
    assert len(events) == 1
    ev = events[0]
    assert ev.metadata["avg_speed"] > 100.0
    assert "Eastbound" in ev.metadata["direction"]

    # Compress into track spans
    spans = compress_events_into_track_spans(events)
    assert len(spans) == 1
    span = spans[0]
    assert span.track_id == "42"
    assert "Eastbound" in span.direction
    assert span.avg_speed > 100.0

    # Build prompt context
    context = build_compact_forensic_context(
        video_name="test_crash.mp4",
        raw_events=events,
    )
    assert "Heading: Eastbound" in context
    assert "Speed:" in context


def test_robbery_and_theft_reconstruction_rules():
    """Verify robbery, theft, fleeing, and suspect-vehicle coordination events."""
    reconstructor = OpenCVForensicReconstructor()
    base_time = datetime(2026, 9, 4, 23, 30, 0, tzinfo=timezone.utc)  # Off-hours (11:30 PM)

    class MockDet:
        def __init__(self, fn, ts, bbox, vel, obj_type, track_id):
            self.frame_number = fn
            self.timestamp_seconds = ts
            self.bbox = bbox
            self.velocity = vel
            self.object_type = obj_type
            self.track_id = track_id
            self.confidence = 0.90

    # Person 1: Loiters, then flees rapidly at high speed
    # Vehicle 1: Idling nearby and leaves synchronously (Getaway coordination)
    # Person 2: Converges with Person 1
    dets = [
        (0.0, [
            MockDet(0, 0.0, (100.0, 100.0, 140.0, 200.0), (0.0, 0.0), "person", 1),
            MockDet(0, 0.0, (500.0, 400.0, 700.0, 500.0), (0.0, 0.0), "car", 2),
            MockDet(0, 0.0, (110.0, 105.0, 150.0, 205.0), (0.0, 0.0), "person", 3),
        ]),
        (1.0, [
            MockDet(1, 1.0, (105.0, 100.0, 145.0, 200.0), (5.0, 0.0), "person", 1),
            MockDet(1, 1.0, (500.0, 400.0, 700.0, 500.0), (0.0, 0.0), "car", 2),
            MockDet(1, 1.0, (115.0, 105.0, 155.0, 205.0), (5.0, 0.0), "person", 3),
        ]),
        (2.0, [
            # Person 1 sprints away to (400, 100) -> 300px in 1s (speed 300px/s)
            MockDet(2, 2.0, (400.0, 100.0, 440.0, 200.0), (300.0, 0.0), "person", 1),
            # Car departs
            MockDet(2, 2.0, (650.0, 400.0, 850.0, 500.0), (150.0, 0.0), "car", 2),
        ]),
    ]

    events, summary = reconstructor.reconstruct_from_detections(
        dets,
        video_start_time=base_time,
        video_id="robbery_vid",
        camera_id="CH-01",
    )

    event_types = [e.event_type for e in events]
    assert "RAPID_EGRESS_FLEEING" in event_types
    assert "SUSPECT_VEHICLE_COORDINATION" in event_types
    assert "MULTI_PERSON_CONVERGENCE" in event_types
    assert "OFF_HOURS_PERIMETER_BREACH" in event_types
    assert "Rapid Fleeing Detected" in summary.headline


def test_vehicle_collision_and_crash_detection():
    """Verify detection of vehicle-to-vehicle physical impact and collision."""
    reconstructor = OpenCVForensicReconstructor()
    base_time = datetime(2026, 9, 4, 14, 0, 0, tzinfo=timezone.utc)

    class MockDet:
        def __init__(self, fn, ts, bbox, vel, obj_type, track_id):
            self.frame_number = fn
            self.timestamp_seconds = ts
            self.bbox = bbox
            self.velocity = vel
            self.object_type = obj_type
            self.track_id = track_id
            self.confidence = 0.92

    # Two vehicles moving perpendicular / head-on towards an intersection and colliding at ts=1.0
    dets = [
        (0.0, [
            # Vehicle 1 moving Eastbound: center (150, 300)
            MockDet(0, 0.0, (100.0, 250.0, 200.0, 350.0), (100.0, 0.0), "car", 10),
            # Vehicle 2 moving Northbound: center (300, 450)
            MockDet(0, 0.0, (250.0, 400.0, 350.0, 500.0), (0.0, -100.0), "truck", 20),
        ]),
        (1.0, [
            # Collision impact point: both overlap at (280, 290) -> IoU > 0.3
            MockDet(1, 1.0, (250.0, 260.0, 350.0, 360.0), (30.0, 0.0), "car", 10),
            MockDet(1, 1.0, (260.0, 270.0, 360.0, 370.0), (0.0, -20.0), "truck", 20),
        ]),
        (2.0, [
            # Post-impact stationary debris / stopped vehicles
            MockDet(2, 2.0, (260.0, 265.0, 360.0, 365.0), (0.0, 0.0), "car", 10),
            MockDet(2, 2.0, (265.0, 275.0, 365.0, 375.0), (0.0, 0.0), "truck", 20),
        ]),
    ]

    events, summary = reconstructor.reconstruct_from_detections(
        dets,
        video_start_time=base_time,
        video_id="crash_vid",
        camera_id="CH-01",
    )

    event_types = [e.event_type for e in events]
    assert "VEHICLE_COLLISION_DETECTED" in event_types
    collision_ev = next(e for e in events if e.event_type == "VEHICLE_COLLISION_DETECTED")
    assert "CRITICAL INCIDENT: Vehicle Collision" in collision_ev.title
    assert "10" in collision_ev.title and "20" in collision_ev.title
    assert "CRITICAL: Traffic Collision" in summary.headline
    assert summary.metadata.get("crash_count", 0) >= 1

