"""
Tests for container timestamp anchoring in ForensicDiskCarverParser.

Note: validates plumbing only, not real-DVR reliability.
"""

import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
import pytest

from backend.parsers.carver.parser import ForensicDiskCarverParser


@pytest.fixture
def ffmpeg_available():
    return shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


def _create_stream_disk_image(out_img: Path, stream_file: Path) -> Path:
    with open(stream_file, "rb") as sf:
        data = sf.read()
    with open(out_img, "wb") as f:
        f.write(b"\x00" * 1024)
        f.write(data)
        f.write(b"\x00" * 1024)
    return out_img


class TestCarverTimestampAnchoring:
    """validates plumbing only, not real-DVR reliability"""

    def test_valid_mp4_timestamp_anchoring(self, tmp_path, ffmpeg_available):
        """validates plumbing only, not real-DVR reliability"""
        if not ffmpeg_available:
            pytest.skip("ffmpeg/ffprobe not available")

        mp4_file = tmp_path / "valid.mp4"
        subprocess.run([
            "ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc=duration=1:size=320x240:rate=1",
            "-metadata", "creation_time=2023-05-14T10:30:00Z",
            "-c:v", "libx264", str(mp4_file),
        ], capture_output=True, check=True)

        img_path = _create_stream_disk_image(tmp_path / "test_valid_mp4.dd", mp4_file)
        parser = ForensicDiskCarverParser()
        res = parser.parse(str(img_path), str(tmp_path / "out"))

        assert res.success is True
        assert len(res.recordings) >= 1
        rec = res.recordings[0]
        assert rec.original_timestamp is not None
        assert rec.original_timestamp.year == 2023
        assert rec.original_timestamp.month == 5
        assert rec.original_timestamp.day == 14
        assert rec.normalized_timestamp is None
        assert rec.raw_metadata.get("timestamp_source") == "container_creation_time"
        assert rec.raw_metadata.get("timestamp_confidence") == "low"
        assert rec.raw_metadata.get("timestamp_tz_known") is False

    def test_epoch_zero_1904_rejected(self, tmp_path, ffmpeg_available):
        """validates plumbing only, not real-DVR reliability"""
        if not ffmpeg_available:
            pytest.skip("ffmpeg/ffprobe not available")

        mp4_file = tmp_path / "epoch_1904.mp4"
        subprocess.run([
            "ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc=duration=1:size=320x240:rate=1",
            "-metadata", "creation_time=1904-01-01T00:00:00Z",
            "-c:v", "libx264", str(mp4_file),
        ], capture_output=True, check=True)

        img_path = _create_stream_disk_image(tmp_path / "test_1904.dd", mp4_file)
        parser = ForensicDiskCarverParser()
        res = parser.parse(str(img_path), str(tmp_path / "out"))

        assert res.success is True
        assert len(res.recordings) >= 1
        rec = res.recordings[0]
        assert rec.original_timestamp is None
        assert rec.normalized_timestamp is None
        assert rec.raw_metadata.get("timestamp_source") is None

    def test_epoch_zero_1970_rejected(self, tmp_path, ffmpeg_available):
        """validates plumbing only, not real-DVR reliability"""
        if not ffmpeg_available:
            pytest.skip("ffmpeg/ffprobe not available")

        mp4_file = tmp_path / "epoch_1970.mp4"
        subprocess.run([
            "ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc=duration=1:size=320x240:rate=1",
            "-metadata", "creation_time=1970-01-01T00:00:00Z",
            "-c:v", "libx264", str(mp4_file),
        ], capture_output=True, check=True)

        img_path = _create_stream_disk_image(tmp_path / "test_1970.dd", mp4_file)
        parser = ForensicDiskCarverParser()
        res = parser.parse(str(img_path), str(tmp_path / "out"))

        assert res.success is True
        assert len(res.recordings) >= 1
        rec = res.recordings[0]
        assert rec.original_timestamp is None
        assert rec.normalized_timestamp is None
        assert rec.raw_metadata.get("timestamp_source") is None

    def test_epoch_zero_2001_rejected(self, tmp_path, ffmpeg_available):
        """validates plumbing only, not real-DVR reliability"""
        if not ffmpeg_available:
            pytest.skip("ffmpeg/ffprobe not available")

        mkv_file = tmp_path / "epoch_2001.mkv"
        subprocess.run([
            "ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc=duration=1:size=320x240:rate=1",
            "-metadata", "creation_time=2001-01-01T00:00:00Z",
            "-c:v", "libx264", str(mkv_file),
        ], capture_output=True, check=True)

        img_path = _create_stream_disk_image(tmp_path / "test_2001.dd", mkv_file)
        parser = ForensicDiskCarverParser()
        res = parser.parse(str(img_path), str(tmp_path / "out"))

        assert res.success is True
        assert len(res.recordings) >= 1
        rec = res.recordings[0]
        assert rec.original_timestamp is None
        assert rec.normalized_timestamp is None
        assert rec.raw_metadata.get("timestamp_source") is None

    def test_ancient_pre_2000_rejected(self, tmp_path, ffmpeg_available):
        """validates plumbing only, not real-DVR reliability"""
        if not ffmpeg_available:
            pytest.skip("ffmpeg/ffprobe not available")

        mp4_file = tmp_path / "ancient.mp4"
        subprocess.run([
            "ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc=duration=1:size=320x240:rate=1",
            "-metadata", "creation_time=1999-12-31T23:59:59Z",
            "-c:v", "libx264", str(mp4_file),
        ], capture_output=True, check=True)

        img_path = _create_stream_disk_image(tmp_path / "test_ancient.dd", mp4_file)
        parser = ForensicDiskCarverParser()
        res = parser.parse(str(img_path), str(tmp_path / "out"))

        assert res.success is True
        assert len(res.recordings) >= 1
        rec = res.recordings[0]
        assert rec.original_timestamp is None
        assert rec.normalized_timestamp is None
        assert rec.raw_metadata.get("timestamp_source") is None

    def test_future_timestamp_rejected(self, tmp_path, ffmpeg_available):
        """validates plumbing only, not real-DVR reliability"""
        if not ffmpeg_available:
            pytest.skip("ffmpeg/ffprobe not available")

        mp4_file = tmp_path / "future.mp4"
        subprocess.run([
            "ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc=duration=1:size=320x240:rate=1",
            "-metadata", "creation_time=2099-01-01T00:00:00Z",
            "-c:v", "libx264", str(mp4_file),
        ], capture_output=True, check=True)

        img_path = _create_stream_disk_image(tmp_path / "test_future.dd", mp4_file)
        parser = ForensicDiskCarverParser()
        res = parser.parse(str(img_path), str(tmp_path / "out"))

        assert res.success is True
        assert len(res.recordings) >= 1
        rec = res.recordings[0]
        assert rec.original_timestamp is None
        assert rec.normalized_timestamp is None
        assert rec.raw_metadata.get("timestamp_source") is None

    def test_missing_timestamp_leaves_none(self, tmp_path, ffmpeg_available):
        """validates plumbing only, not real-DVR reliability"""
        if not ffmpeg_available:
            pytest.skip("ffmpeg/ffprobe not available")

        mp4_file = tmp_path / "missing.mp4"
        subprocess.run([
            "ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc=duration=1:size=320x240:rate=1",
            "-map_metadata", "-1",
            "-c:v", "libx264", str(mp4_file),
        ], capture_output=True, check=True)

        img_path = _create_stream_disk_image(tmp_path / "test_missing.dd", mp4_file)
        parser = ForensicDiskCarverParser()
        res = parser.parse(str(img_path), str(tmp_path / "out"))

        assert res.success is True
        assert len(res.recordings) >= 1
        rec = res.recordings[0]
        # In case ffmpeg injects its own encoder creation_time, if any creation_time is valid it might be anchored,
        # but if omitted/stripped or absent it stays None.
        # Let's verify raw_metadata timestamp structure is well-formed
        assert rec.normalized_timestamp is None
        assert "timestamp_source" in rec.raw_metadata

    def test_valid_mkv_timestamp_anchoring(self, tmp_path, ffmpeg_available):
        """validates plumbing only, not real-DVR reliability"""
        if not ffmpeg_available:
            pytest.skip("ffmpeg/ffprobe not available")

        mkv_file = tmp_path / "valid.mkv"
        subprocess.run([
            "ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc=duration=1:size=320x240:rate=1",
            "-metadata", "creation_time=2022-08-15T14:20:00Z",
            "-c:v", "libx264", str(mkv_file),
        ], capture_output=True, check=True)

        img_path = _create_stream_disk_image(tmp_path / "test_valid_mkv.dd", mkv_file)
        parser = ForensicDiskCarverParser()
        res = parser.parse(str(img_path), str(tmp_path / "out"))

        assert res.success is True
        assert len(res.recordings) >= 1
        rec = res.recordings[0]
        assert rec.original_timestamp is not None
        assert rec.original_timestamp.year == 2022
        assert rec.original_timestamp.month == 8
        assert rec.original_timestamp.day == 15
        assert rec.normalized_timestamp is None
        assert rec.raw_metadata.get("timestamp_source") == "container_creation_time"
        assert rec.raw_metadata.get("timestamp_confidence") == "low"
        assert rec.raw_metadata.get("timestamp_tz_known") is False

    def test_valid_avi_timestamp_anchoring(self, tmp_path, ffmpeg_available):
        """validates plumbing only, not real-DVR reliability"""
        if not ffmpeg_available:
            pytest.skip("ffmpeg/ffprobe not available")

        avi_file = tmp_path / "valid.avi"
        subprocess.run([
            "ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc=duration=1:size=320x240:rate=1",
            "-metadata", "date=2023-03-20 18:00:00",
            "-metadata", "creation_time=2023-03-20 18:00:00",
            "-c:v", "rawvideo", str(avi_file),
        ], capture_output=True, check=True)

        img_path = _create_stream_disk_image(tmp_path / "test_valid_avi.dd", avi_file)
        parser = ForensicDiskCarverParser()
        res = parser.parse(str(img_path), str(tmp_path / "out"))

        assert res.success is True
        assert len(res.recordings) >= 1
        rec = res.recordings[0]
        assert rec.original_timestamp is not None
        assert rec.original_timestamp.year == 2023
        assert rec.original_timestamp.month == 3
        assert rec.original_timestamp.day == 20
        assert rec.normalized_timestamp is None
        assert rec.raw_metadata.get("timestamp_source") == "container_creation_time"
        assert rec.raw_metadata.get("timestamp_confidence") == "low"
        assert rec.raw_metadata.get("timestamp_tz_known") is False

    def test_untouched_stream_types_leave_timestamp_none(self):
        """validates plumbing only, not real-DVR reliability"""
        from backend.parsers.carver.parser import _extract_container_timestamp
        probe_sample = {
            "format": {"tags": {"creation_time": "2023-05-14T10:30:00Z"}},
            "streams": [],
        }
        for unhandled in ["dhav", "mpeg_ps", "flv", "h264", "hevc", "unknown"]:
            dt, src, conf, tz = _extract_container_timestamp(unhandled, probe_sample)
            assert dt is None
            assert src is None
            assert conf is None
            assert tz is None
