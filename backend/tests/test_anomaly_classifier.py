"""backend/tests/test_anomaly_classifier.py — Tests for UCF-Crime and XD-Violence anomaly classifier."""

from datetime import datetime, timezone, timedelta
import pytest

from backend.video.analysis.models import Detection
from backend.ai.events.anomaly_classifier import (
    detect_assault,
    detect_fighting,
    detect_robbery,
    detect_road_accident,
    detect_crowd_panic,
    detect_vandalism,
    detect_shoplifting,
    classify_anomalies,
)


def test_detect_assault():
    t0 = datetime(2026, 9, 7, 10, 0, 0, tzinfo=timezone.utc)
    t1 = t0 + timedelta(seconds=0.5)

    # Person 1 rapidly approaches Person 2, resulting in overlapping bboxes
    p1_f1 = Detection(
        video_id="v1", camera_id="c1", frame_number=1, timestamp=t0,
        object_type="person", confidence=0.9, bbox=(10.0, 10.0, 50.0, 100.0), track_id=1,
    )
    p2_f1 = Detection(
        video_id="v1", camera_id="c1", frame_number=1, timestamp=t0,
        object_type="person", confidence=0.9, bbox=(100.0, 10.0, 140.0, 100.0), track_id=2,
    )

    p1_f2 = Detection(
        video_id="v1", camera_id="c1", frame_number=2, timestamp=t1,
        object_type="person", confidence=0.9, bbox=(90.0, 10.0, 130.0, 100.0), track_id=1,
    )
    p2_f2 = Detection(
        video_id="v1", camera_id="c1", frame_number=2, timestamp=t1,
        object_type="person", confidence=0.9, bbox=(100.0, 10.0, 140.0, 100.0), track_id=2,
    )

    events = detect_assault([p1_f1, p2_f1, p1_f2, p2_f2])
    assert len(events) >= 1
    assert events[0].event_type == "ANOMALY_ASSAULT"
    assert "UCF-Crime" in events[0].metadata["dataset_reference"]


def test_detect_road_accident():
    t0 = datetime(2026, 9, 7, 10, 0, 0, tzinfo=timezone.utc)

    # 2 vehicles colliding with significant IoU and speed metadata
    veh1 = Detection(
        video_id="v1", camera_id="c1", frame_number=5, timestamp=t0,
        object_type="car", confidence=0.85, bbox=(100.0, 100.0, 200.0, 200.0), track_id=1,
        metadata={"velocity": (40.0, 0.0)},
    )
    veh2 = Detection(
        video_id="v1", camera_id="c1", frame_number=5, timestamp=t0,
        object_type="truck", confidence=0.90, bbox=(150.0, 100.0, 250.0, 200.0), track_id=2,
        metadata={"velocity": (-30.0, 0.0)},
    )

    events = detect_road_accident([veh1, veh2])
    assert len(events) == 1
    assert events[0].event_type == "ANOMALY_ROAD_ACCIDENT"


def test_classify_anomalies_empty_or_safe():
    assert classify_anomalies([]) == []

    t0 = datetime(2026, 9, 7, 10, 0, 0, tzinfo=timezone.utc)
    single_person = [
        Detection(
            video_id="v1", camera_id="c1", frame_number=1, timestamp=t0,
            object_type="person", confidence=0.9, bbox=(10.0, 10.0, 50.0, 100.0), track_id=1,
            metadata={"velocity": (2.0, 1.0)},
        )
    ]
    events = classify_anomalies(single_person)
    assert events == []
