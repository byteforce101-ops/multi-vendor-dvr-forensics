"""
Tests for container timestamp anchoring in ForensicDiskCarverParser.

Note: validates plumbing only, not real-DVR reliability.
"""

import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
import pytest

from backend.parsers.carver.parser import ForensicDiskCarverParser, _extract_container_timestamp
from backend.parsers.common.base import NormalizedRecording


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
        assert rec.original_timestamp.tzinfo == timezone.utc
        assert rec.normalized_timestamp is None
        assert rec.raw_metadata.get("timestamp_source") == "container_creation_time"
        assert rec.raw_metadata.get("timestamp_confidence") == "low"
        assert rec.raw_metadata.get("timestamp_tz_known") is False
        assert rec.raw_metadata.get("timestamp_tag") == "creation_time"

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
        assert rec.raw_metadata.get("timestamp_tag") is None

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
        assert rec.raw_metadata.get("timestamp_tag") is None

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
        assert rec.raw_metadata.get("timestamp_tag") is None

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
        assert rec.raw_metadata.get("timestamp_tag") is None

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
        assert rec.raw_metadata.get("timestamp_tag") is None

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
        assert rec.original_timestamp.tzinfo == timezone.utc
        assert rec.normalized_timestamp is None
        assert rec.raw_metadata.get("timestamp_source") == "container_creation_time"
        assert rec.raw_metadata.get("timestamp_confidence") == "low"
        assert rec.raw_metadata.get("timestamp_tz_known") is False
        assert rec.raw_metadata.get("timestamp_tag") == "creation_time"

    def test_avi_idit_timestamp_anchoring(self, tmp_path, ffmpeg_available):
        """validates plumbing only, not real-DVR reliability"""
        if not ffmpeg_available:
            pytest.skip("ffmpeg/ffprobe not available")

        import struct
        avi_file = tmp_path / "clean.avi"
        subprocess.run([
            "ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc=duration=1:size=320x240:rate=1",
            "-c:v", "rawvideo", str(avi_file),
        ], capture_output=True, check=True)

        data = bytearray(avi_file.read_bytes())
        # Inject standard RIFF LIST INFO chunk with IDIT sub-chunk
        ts_bytes = b"2023-03-20 18:00:00\x00"
        if len(ts_bytes) % 2 != 0:
            ts_bytes += b"\x00"
        idit_chunk = b"IDIT" + struct.pack("<I", len(ts_bytes)) + ts_bytes
        list_info = b"LIST" + struct.pack("<I", 4 + len(idit_chunk)) + b"INFO" + idit_chunk

        hdrl_pos = data.find(b"LIST")
        hdrl_len = struct.unpack("<I", data[hdrl_pos + 4 : hdrl_pos + 8])[0]
        insert_pos = hdrl_pos + 8 + hdrl_len

        riff_sz = struct.unpack("<I", data[4:8])[0]
        data[4:8] = struct.pack("<I", riff_sz + len(list_info))
        data[insert_pos:insert_pos] = list_info

        injected_avi = tmp_path / "injected_idit.avi"
        injected_avi.write_bytes(data)

        img_path = _create_stream_disk_image(tmp_path / "test_valid_avi_idit.dd", injected_avi)
        parser = ForensicDiskCarverParser()
        res = parser.parse(str(img_path), str(tmp_path / "out_avi"))

        assert res.success is True
        assert len(res.recordings) >= 1
        rec = res.recordings[0]
        assert rec.original_timestamp is not None
        assert rec.original_timestamp.year == 2023
        assert rec.original_timestamp.month == 3
        assert rec.original_timestamp.day == 20
        assert rec.original_timestamp.tzinfo == timezone.utc
        assert rec.normalized_timestamp is None
        assert rec.raw_metadata.get("timestamp_source") == "container_creation_time"
        assert rec.raw_metadata.get("timestamp_confidence") == "low"
        assert rec.raw_metadata.get("timestamp_tz_known") is False
        assert rec.raw_metadata.get("timestamp_tag") == "IDIT"

    def test_avi_date_tag_ignored(self):
        """validates plumbing only, not real-DVR reliability"""
        probe_data = {
            "format": {
                "tags": {
                    "date": "2023-03-20 18:00:00",
                }
            },
            "streams": [],
        }
        dt, src, conf, tz_known, tag = _extract_container_timestamp("avi", probe_data)
        assert dt is None
        assert src is None
        assert conf is None
        assert tz_known is None
        assert tag is None

    def test_untouched_stream_types_leave_timestamp_none(self):
        """validates plumbing only, not real-DVR reliability"""
        probe_sample = {
            "format": {"tags": {"creation_time": "2023-05-14T10:30:00Z"}},
            "streams": [],
        }
        for unhandled in ["dhav", "mpeg_ps", "flv", "h264", "hevc", "unknown"]:
            dt, src, conf, tz, tag = _extract_container_timestamp(unhandled, probe_sample)
            assert dt is None
            assert src is None
            assert conf is None
            assert tz is None
            assert tag is None

    def test_sort_hikvision_and_carved_recordings_together(self):
        """
        validates plumbing only, not real-DVR reliability.
        Ensures carved original_timestamp (UTC timezone-aware) sorts seamlessly
        with HikvisionParser original_timestamp without TypeError.
        """
        hik_rec = NormalizedRecording(
            camera_id="CH-01",
            recording_id="hik-000001",
            source_path="/fake/hik.dd",
            extracted_path=None,
            original_timestamp=datetime(2023, 5, 14, 9, 0, 0, tzinfo=timezone.utc),
            normalized_timestamp=None,
            duration_seconds=60.0,
            resolution="1920x1080",
            fps=25.0,
            codec="h264",
            file_size=1024,
            recovery_status="ORIGINAL",
        )
        carved_rec = NormalizedRecording(
            camera_id="CH-02",
            recording_id="carved-001_mp4",
            source_path="/fake/carved.dd",
            extracted_path=None,
            original_timestamp=datetime(2023, 5, 14, 10, 30, 0, tzinfo=timezone.utc),
            normalized_timestamp=None,
            duration_seconds=60.0,
            resolution="1920x1080",
            fps=25.0,
            codec="h264",
            file_size=1024,
            recovery_status="RECOVERED",
        )

        recordings = [carved_rec, hik_rec]
        sorted_recs = sorted(recordings, key=lambda r: r.original_timestamp)
        assert sorted_recs[0].recording_id == "hik-000001"
        assert sorted_recs[1].recording_id == "carved-001_mp4"
