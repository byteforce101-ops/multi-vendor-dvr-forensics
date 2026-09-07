"""backend/tests/test_collision_detection.py — Tests for multi-vehicle and dashcam collision detection heuristics."""

from datetime import datetime, timezone, timedelta
import pytest

from backend.video.analysis.models import Detection
from backend.ai.events.incident_heuristics import (
    detect_proximity_events,
    detect_ego_collision_events,
    detect_sudden_stop_events,
    detect_incident_candidates,
    _box_distance,
)


def test_box_distance_calculation():
    """Verify edge-to-edge box distance math."""
    box_a = (10.0, 10.0, 30.0, 30.0)
    box_b = (40.0, 10.0, 60.0, 30.0)  # 10px horizontal gap
    assert _box_distance(box_a, box_b) == 10.0

    box_overlap = (20.0, 20.0, 40.0, 40.0)  # overlapping box_a
    assert _box_distance(box_a, box_overlap) == 0.0


def test_detect_proximity_and_edge_contact():
    """Verify multi-vehicle contact and proximity flagging on corner/edge touches."""
    t0 = datetime(2026, 9, 7, 10, 0, 0, tzinfo=timezone.utc)

    # 2 vehicles with 8px edge gap (close contact impact)
    det1 = Detection(
        video_id="v1",
        camera_id="cam1",
        frame_number=10,
        timestamp=t0,
        object_type="car",
        confidence=0.88,
        bbox=(100.0, 150.0, 200.0, 250.0),
        track_id=1,
    )
    det2 = Detection(
        video_id="v1",
        camera_id="cam1",
        frame_number=10,
        timestamp=t0,
        object_type="truck",
        confidence=0.92,
        bbox=(208.0, 150.0, 320.0, 260.0),  # 8px from det1
        track_id=2,
    )

    events = detect_proximity_events([det1, det2])
    assert len(events) == 1
    assert "REVIEW_FLAG_POSSIBLE_CONTACT" in events[0].event_type
    assert events[0].metadata["object_a"] == "car"
    assert events[0].metadata["object_b"] == "truck"


def test_detect_dashcam_ego_collision():
    """Verify dashcam front-impact looming detection where vehicle ahead rapidly expands towards camera."""
    t0 = datetime(2026, 9, 7, 12, 0, 0, tzinfo=timezone.utc)

    # Approaching vehicle grows from small distant car to massive close-up on windshield
    det1 = Detection(
        video_id="dashcam",
        camera_id="cam_front",
        frame_number=1,
        timestamp=t0,
        object_type="car",
        confidence=0.85,
        bbox=(280.0, 150.0, 360.0, 210.0),  # w=80, h=60, area=4800
        track_id=5,
    )
    det2 = Detection(
        video_id="dashcam",
        camera_id="cam_front",
        frame_number=2,
        timestamp=t0 + timedelta(seconds=0.25),
        object_type="car",
        confidence=0.90,
        bbox=(200.0, 180.0, 440.0, 360.0),  # w=240, h=180, area=43200 (9x expansion!)
        track_id=5,
    )

    events = detect_ego_collision_events([det1, det2])
    assert len(events) == 1
    assert events[0].event_type == "REVIEW_FLAG_EGO_COLLISION_WARNING"
    assert events[0].track_id == 5
    assert events[0].metadata["reason"] == "rapid_looming_approach"


def test_detect_sudden_stop_deceleration():
    """Verify sudden stop heuristic flags sharp vehicle deceleration on impact."""
    t0 = datetime(2026, 9, 7, 14, 0, 0, tzinfo=timezone.utc)

    # Vehicle was moving fast at 100 px/s, then halts upon collision to 5 px/s
    det1 = Detection(
        video_id="v1",
        camera_id="cam1",
        frame_number=1,
        timestamp=t0,
        object_type="car",
        confidence=0.89,
        bbox=(100.0, 200.0, 160.0, 250.0),  # cx=130
        track_id=7,
    )
    det2 = Detection(
        video_id="v1",
        camera_id="cam1",
        frame_number=2,
        timestamp=t0 + timedelta(seconds=0.25),
        object_type="car",
        confidence=0.91,
        bbox=(125.0, 200.0, 185.0, 250.0),  # cx=155 -> moved 25px in 0.25s = 100 px/s
        track_id=7,
    )
    det3 = Detection(
        video_id="v1",
        camera_id="cam1",
        frame_number=3,
        timestamp=t0 + timedelta(seconds=0.50),
        object_type="car",
        confidence=0.92,
        bbox=(126.0, 200.0, 186.0, 250.0),  # cx=156 -> moved 1px in 0.25s = 4 px/s (96% drop!)
        track_id=7,
    )

    events = detect_sudden_stop_events([det1, det2, det3])
    assert len(events) >= 1
    assert any(e.event_type == "REVIEW_FLAG_SUDDEN_STOP" for e in events)


def test_detect_incident_candidates_wrapper():
    """Verify combined incident candidates wrapper."""
    t0 = datetime(2026, 9, 7, 15, 0, 0, tzinfo=timezone.utc)

    det1 = Detection(
        video_id="v1",
        camera_id="cam1",
        frame_number=1,
        timestamp=t0,
        object_type="car",
        confidence=0.88,
        bbox=(100.0, 150.0, 200.0, 250.0),
        track_id=1,
    )
    det2 = Detection(
        video_id="v1",
        camera_id="cam1",
        frame_number=1,
        timestamp=t0,
        object_type="car",
        confidence=0.88,
        bbox=(105.0, 150.0, 205.0, 250.0),  # High IoU overlap
        track_id=2,
    )

    candidates = detect_incident_candidates([det1, det2])
    assert len(candidates) >= 1
    assert any("POSSIBLE_CONTACT" in c.event_type for c in candidates)
