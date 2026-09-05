"""
Tests for deep NAL carving and Hikvision deleted footage recovery from raw disk images.
"""

from pathlib import Path
import pytest
from backend.parsers.hikvision.parser import HikvisionParser
from backend.parsers.carver.parser import ForensicDiskCarverParser
from backend.parsers.registry import ParserManager


NORMAL_DD = Path("backend/tests/fixtures/hikvision_normal.dd")
DELETED_DD = Path("backend/tests/fixtures/hikvision_deleted.dd")


def test_hikvision_normal_parse_and_extract(tmp_path):
    """Test parsing and extraction of normal indexed Hikvision disk image."""
    assert NORMAL_DD.exists(), "hikvision_normal.dd must exist"

    parser = HikvisionParser()
    matched, conf, info = parser.detect(str(NORMAL_DD))
    assert matched is True
    assert conf > 0.8
    assert info["vendor"] == "hikvision"

    out_dir = tmp_path / "normal_out"
    res = parser.parse(str(NORMAL_DD), str(out_dir))
    assert res.success is True
    assert len(res.recordings) >= 1

    # Normal recording should have ORIGINAL recovery_status
    normal_recs = [r for r in res.recordings if r.recovery_status == "ORIGINAL"]
    assert len(normal_recs) == 1
    assert normal_recs[0].camera_id == "CH-01"

    # Extract to playable MP4
    extract_res = parser.extract_recordings(
        str(NORMAL_DD), str(out_dir), res.recordings, res.raw_master_block
    )
    assert extract_res.success is True
    extracted_file = extract_res.recordings[0].extracted_path
    assert extracted_file is not None
    assert Path(extracted_file).exists()
    assert Path(extracted_file).stat().st_size > 10000


def test_hikvision_deleted_recovery_and_extract(tmp_path):
    """Test carving & recovery of deleted unindexed footage from Hikvision disk image."""
    assert DELETED_DD.exists(), "hikvision_deleted.dd must exist"

    parser = HikvisionParser()
    matched, conf, info = parser.detect(str(DELETED_DD))
    assert matched is True
    assert conf > 0.8

    out_dir = tmp_path / "deleted_out"
    res = parser.parse(str(DELETED_DD), str(out_dir))
    assert res.success is True
    assert len(res.recordings) >= 1

    # Should be recovered with RECOVERED status
    recovered_recs = [r for r in res.recordings if r.recovery_status == "RECOVERED"]
    assert len(recovered_recs) >= 1
    assert recovered_recs[0].raw_metadata.get("is_deleted_carved") is True

    # Extract to playable MP4
    extract_res = parser.extract_recordings(
        str(DELETED_DD), str(out_dir), res.recordings, res.raw_master_block
    )
    assert extract_res.success is True
    extracted_file = extract_res.recordings[0].extracted_path
    assert extracted_file is not None
    assert Path(extracted_file).exists()
    assert Path(extracted_file).stat().st_size > 10000


def test_carver_deep_nal_raw_stream(tmp_path):
    """Test deep H.264 NAL carver on raw unallocated sectors."""
    raw_disk_path = tmp_path / "raw_h264_disk.raw"

    # Create synthetic raw disk with wipe pattern and raw H.264 Annex-B NAL stream
    with open(raw_disk_path, "wb") as f:
        f.write(b"\x55" * 1024)  # Sector noise / unallocated slack

        # SPS (type 7)
        f.write(b"\x00\x00\x00\x01\x67\x42\x00\x1f\x96\x35\x40\xf0\x04\x4f\xcb\x37\x01\x01\x01\x40")
        # PPS (type 8)
        f.write(b"\x00\x00\x00\x01\x68\xce\x3c\x80")
        # IDR Keyframe slice (type 5)
        f.write(b"\x00\x00\x00\x01\x65\x88\x84\x00\x10\xff\x00" + b"\x12" * 500)

        # Non-IDR slices (type 1)
        for _ in range(15):
            f.write(b"\x00\x00\x00\x01\x41\x9a\x00\x01" + b"\x34" * 300)

        f.write(b"\x55" * 2048)

    carver = ForensicDiskCarverParser()
    matched, conf, info = carver.detect(str(raw_disk_path))
    assert matched is True
    assert "h264" in info["stream_types"]

    out_dir = tmp_path / "carved_out"
    res = carver.parse(str(raw_disk_path), str(out_dir))
    assert res.success is True
    assert len(res.recordings) >= 1
    assert res.recordings[0].recovery_status == "RECOVERED"
