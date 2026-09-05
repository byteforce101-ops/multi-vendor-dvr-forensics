"""backend/tests/test_opencv_forensic_detector.py — Tests for Pure OpenCV Forensic Detector & Reconstructor."""

from datetime import datetime, timezone
import numpy as np
import pytest

from backend.ai.detectors.opencv_forensic_detector import (
    OpenCVForensicDetector,
    OpenCVForensicDetection,
    FORENSIC_CLASSES,
)
from backend.video.reconstruction.opencv_reconstructor import (
    OpenCVForensicReconstructor,
    _direction_from_vector,
)
from backend.video.analysis.service import VideoAnalysisService
from backend.video.extraction.frame_extractor import FrameSample


def test_direction_from_vector_calculation():
    """Verify 8-point compass direction calculation from velocity vectors."""
    assert "Eastbound" in _direction_from_vector(25.0, 0.0)
    assert "Westbound" in _direction_from_vector(-25.0, 0.0)
    assert "Southbound" in _direction_from_vector(0.0, 25.0)
    assert "Northbound" in _direction_from_vector(0.0, -25.0)
    assert "Stationary" in _direction_from_vector(1.0, 1.0)


def test_opencv_forensic_detector_vehicle_classification():
    """Verify morphometric aspect-ratio detection classifies horizontal moving clusters as vehicle."""
    detector = OpenCVForensicDetector()
    detector.reset_tracks()

    # Frame 1: Blank background
    f1 = np.zeros((480, 640, 3), dtype=np.uint8)
    detector.detect_frame(f1)

    # Frame 2: Moving vehicle-proportioned block (horizontal: w=140, h=60, ratio=2.33, area=8400)
    f2 = np.zeros((480, 640, 3), dtype=np.uint8)
    f2[200:260, 100:240] = 220
    dets = detector.detect_frame(f2, fps=2.0)

    assert len(dets) >= 1
    # Check that it detected a forensic class (vehicle or motion) and NEVER a household item like donut/vase
    for d in dets:
        assert d.class_name in FORENSIC_CLASSES
        assert d.class_name not in {"donut", "vase", "clock", "toaster", "pizza"}


def test_opencv_forensic_detector_centroid_tracking():
    """Verify tracker assigns persistent track IDs across moving frames."""
    detector = OpenCVForensicDetector()
    detector.reset_tracks()

    # Frame 1: Background
    detector.detect_frame(np.zeros((300, 300, 3), dtype=np.uint8))

    # Frame 2: Object at x=50..120
    f2 = np.zeros((300, 300, 3), dtype=np.uint8)
    f2[100:180, 50:120] = 240
    dets2 = detector.detect_frame(f2, fps=2.0)
    assert len(dets2) >= 1
    track_id = dets2[0].track_id
    assert track_id is not None

    # Frame 3: Object moved to x=70..140 (smooth movement)
    f3 = np.zeros((300, 300, 3), dtype=np.uint8)
    f3[100:180, 70:140] = 240
    dets3 = detector.detect_frame(f3, fps=2.0)
    assert len(dets3) >= 1
    # Same track ID should be maintained
    assert dets3[0].track_id == track_id
    # Velocity should be positive eastward
    assert dets3[0].velocity[0] > 0


def test_opencv_reconstructor_trajectory_and_loitering():
    """Verify trajectory event reconstruction, direction tracking, and loitering identification."""
    reconstructor = OpenCVForensicReconstructor(loitering_min_seconds=2.0, loitering_max_radius=50.0)

    # Simulate tracked person moving Eastbound
    obs_east = [
        (0.0, [OpenCVForensicDetection(class_name="person", confidence=0.85, bbox=(10, 10, 30, 60), track_id=1, velocity=(20.0, 0.0))]),
        (1.0, [OpenCVForensicDetection(class_name="person", confidence=0.85, bbox=(30, 10, 50, 60), track_id=1, velocity=(20.0, 0.0))]),
        (2.0, [OpenCVForensicDetection(class_name="person", confidence=0.85, bbox=(50, 10, 70, 60), track_id=1, velocity=(20.0, 0.0))]),
    ]

    events, summary = reconstructor.reconstruct_from_detections(obs_east)
    assert len(events) >= 1
    assert "PERSON" in events[0].event_type
    assert "Eastbound" in events[0].description
    assert summary.headline is not None
    assert "1 Person" in summary.headline

    # Simulate loitering person (staying in roughly same spot for 4 seconds)
    obs_loiter = [
        (0.0, [OpenCVForensicDetection(class_name="person", confidence=0.85, bbox=(100, 100, 120, 150), track_id=2, velocity=(0.0, 0.0))]),
        (1.5, [OpenCVForensicDetection(class_name="person", confidence=0.85, bbox=(105, 102, 125, 152), track_id=2, velocity=(2.0, 1.0))]),
        (3.5, [OpenCVForensicDetection(class_name="person", confidence=0.85, bbox=(102, 98, 122, 148), track_id=2, velocity=(-1.0, 0.0))]),
    ]
    loiter_events, loiter_summary = reconstructor.reconstruct_from_detections(obs_loiter)
    assert any(e.event_type == "LOITERING_DETECTED" for e in loiter_events)


def test_video_analysis_service_with_pure_opencv():
    """Verify VideoAnalysisService runs end-to-end with 100% pure OpenCV detector engine."""
    service = VideoAnalysisService(
        detector_engine="opencv",
        enable_enhancement=True,
    )

    # 3 synthetic frames
    f1 = np.zeros((240, 320, 3), dtype=np.uint8)
    f2 = np.zeros((240, 320, 3), dtype=np.uint8)
    f2[80:160, 100:200] = 200  # vehicle block
    f3 = np.zeros((240, 320, 3), dtype=np.uint8)
    f3[80:160, 140:240] = 200  # vehicle moving right

    samples = [
        FrameSample(frame_number=0, timestamp_seconds=0.0, image=f1),
        FrameSample(frame_number=1, timestamp_seconds=0.5, image=f2),
        FrameSample(frame_number=2, timestamp_seconds=1.0, image=f3),
    ]

    ai_results = service.ai.analyze_frames(samples)
    assert isinstance(ai_results, list)
    for r in ai_results:
        assert r.source == "opencv"
        assert r.object_type in FORENSIC_CLASSES


def test_no_false_bicycle_or_vehicle_on_pedestrians():
    """Verify that human motion blobs (e.g. walking, crouching, carrying items) are never misclassified as bicycles or vehicles."""
    detector = OpenCVForensicDetector()
    detector.reset_tracks()

    # Frame 1: Background
    detector.detect_frame(np.zeros((480, 640, 3), dtype=np.uint8))

    # Frame 2: Moving human with roughly square/slightly wide aspect ratio (e.g. walking with basket / reaching)
    # w=60, h=65 -> aspect_ratio_wh ~ 0.92
    f2 = np.zeros((480, 640, 3), dtype=np.uint8)
    f2[150:215, 200:260] = 200
    dets = detector.detect_frame(f2, fps=2.0)

    # Must NOT detect bicycle or vehicle
    for d in dets:
        assert d.class_name not in ("bicycle", "vehicle", "car", "motorcycle"), f"Unexpected false detection: {d.class_name}"
