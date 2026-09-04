from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from backend.api.main import app
from backend.cli.exit_codes import ExitCode
from backend.cli.main import app as cli_app
from backend.video.analysis.motion import DVRScanMotionDetector, detect_motion
from backend.video.extraction.frame_extractor import FrameSample
import numpy as np

FIXTURE = Path("backend/tests/fixtures/hikvision_synthetic.dd").resolve()
runner = CliRunner()


def test_video_analyze_api_with_dd_image():
    """Test POST /video/analyze with a .dd forensic disk image."""
    with TestClient(app) as client:
        with open(FIXTURE, "rb") as f:
            response = client.post(
                "/video/analyze",
                files={"file": ("hikvision_synthetic.dd", f, "application/octet-stream")},
            )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["vendor"] == "hikvision"
        assert data["forensic_summary"]["headline"] == "Hikvision Forensic Disk Image Analyzed"
        assert data["event_count"] == 3


def test_cli_analyze_with_dd_image():
    """Test dvrforensics analyze with a .dd disk image."""
    result = runner.invoke(cli_app, ["analyze", str(FIXTURE)])
    assert result.exit_code == ExitCode.OK
    assert "Detected forensic disk image" in result.stdout
    assert "hikvision" in result.stdout.lower()


def test_opencv_dvrscan_motion_detector():
    """Test DVRScanMotionDetector OpenCV MOG2 background subtraction."""
    detector = DVRScanMotionDetector(history=10, var_threshold=16.0)

    # Frame 1: solid black background
    frame1 = np.zeros((480, 640, 3), dtype=np.uint8)
    score1, boxes1 = detector.process_frame(frame1)

    # Frame 2: solid black background (no motion)
    frame2 = np.zeros((480, 640, 3), dtype=np.uint8)
    score2, boxes2 = detector.process_frame(frame2)

    # Frame 3: large bright square inserted (motion!)
    frame3 = np.zeros((480, 640, 3), dtype=np.uint8)
    frame3[100:300, 100:300] = 255
    score3, boxes3 = detector.process_frame(frame3)

    assert score3 > score2
    assert len(boxes3) > 0


def test_detect_motion_with_frames():
    """Test detect_motion pipeline with OpenCV MOG2."""
    frames = [
        FrameSample(frame_number=0, timestamp_seconds=0.0, image=np.zeros((100, 100, 3), dtype=np.uint8)),
        FrameSample(frame_number=1, timestamp_seconds=1.0, image=np.zeros((100, 100, 3), dtype=np.uint8)),
        FrameSample(frame_number=2, timestamp_seconds=2.0, image=np.full((100, 100, 3), 255, dtype=np.uint8)),
        FrameSample(frame_number=3, timestamp_seconds=3.0, image=np.full((100, 100, 3), 255, dtype=np.uint8)),
        FrameSample(frame_number=4, timestamp_seconds=4.0, image=np.zeros((100, 100, 3), dtype=np.uint8)),
    ]
    events = detect_motion(frames, threshold=0.05, min_event_seconds=0.5)
    assert isinstance(events, list)


def test_forensic_disk_carver_detection_and_parsing(tmp_path):
    """Test ForensicDiskCarverParser with synthetic multi-stream raw disk image."""
    from backend.parsers.carver.parser import ForensicDiskCarverParser
    from backend.parsers.registry import ParserManager

    # Construct a synthetic raw disk with FLV header and MP4 header
    raw_disk_path = tmp_path / "synthetic_carve.dd"
    with open(raw_disk_path, "wb") as f:
        # 512 bytes wipe pattern
        f.write(b"\xb9" * 512)
        # FLV header (9 bytes) + prev tag size (4) + 1 video tag (15 bytes)
        flv_hdr = b"FLV\x01\x05\x00\x00\x00\x09\x00\x00\x00\x00\x09\x00\x00\x0a\x00\x00\x00\x00\x00\x00\x00" + b"\x00" * 10 + b"\x00\x00\x00\x15"
        f.write(flv_hdr)
        f.write(b"\xb9" * 512)
        # MP4 ftyp box (40 bytes)
        mp4_box = b"\x00\x00\x00(ftypmp42\x00\x00\x00\x01isomiso2avc1mp41mp423gp5"
        # MP4 mdat box (1024 bytes)
        mdat_box = (1024).to_bytes(4, "big") + b"mdat" + (b"\x00" * 1016)
        f.write(mp4_box + mdat_box)

    parser = ForensicDiskCarverParser()
    matched, conf, info = parser.detect(str(raw_disk_path))
    assert matched is True
    assert conf > 0.5
    assert info["vendor"] == "generic_dvr_carver"

    manager = ParserManager()
    best_p, b_conf, _ = manager.detect(str(raw_disk_path))
    assert best_p is not None
    assert best_p.vendor_name == "generic_dvr_carver"


def test_l3_video_dd_if_available():
    """Verify that L3_Video.dd is recognized and parsed without errors if present on system."""
    import os
    l3_path = Path(r"C:\Users\sarthak\Downloads\L3_Video.dd\L3_Video.dd")
    if not l3_path.exists():
        pytest.skip("L3_Video.dd not present in Downloads directory")

    from backend.parsers.registry import ParserManager
    from backend.cli.tui.engine import TraceXPipelineEngine

    manager = ParserManager()
    parser, conf, info = manager.detect(str(l3_path))
    assert parser is not None
    assert parser.vendor_name == "generic_dvr_carver"
    assert info["streams_found"] >= 3

    engine = TraceXPipelineEngine()
    res = engine.run_pipeline(str(l3_path))
    assert res.vendor_name == "generic_dvr_carver"
    assert len(res.parse_recordings) == 3
    assert len(res.recovered_recordings) == 3
    assert len(res.errors) == 0

