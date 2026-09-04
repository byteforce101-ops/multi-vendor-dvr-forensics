"""Fallback parser for standard exported video files (MP4/AVI/MKV) using ffprobe."""

import json
import os
import shutil
import subprocess

from backend.parsers.common.base import (
    BaseDVRParser, ParseResult, ParseError, NormalizedRecording,
)

SUPPORTED_EXTENSIONS = {".mp4", ".avi", ".mkv"}


def _parse_fps(rate_str: str) -> float | None:
    try:
        num, denom = rate_str.split("/")
        return round(int(num) / int(denom), 2) if int(denom) != 0 else None
    except Exception:
        return None


class GenericVideoParser(BaseDVRParser):
    vendor_name = "generic"
    parser_version = "0.1.0"

    def detect(self, evidence_path: str) -> tuple[bool, float, dict]:
        ext = os.path.splitext(evidence_path)[1].lower()
        if ext in SUPPORTED_EXTENSIONS:
            return True, 0.3, {"extension": ext}
        return False, 0.0, {}

    def validate(self, evidence_path: str) -> tuple[bool, list[str]]:
        if shutil.which("ffprobe") is None:
            return False, ["ffprobe not found on PATH"]
        return True, []

    def parse(self, evidence_path: str, output_directory: str) -> ParseResult:
        try:
            proc = subprocess.run(
                ["ffprobe", "-v", "quiet", "-print_format", "json",
                 "-show_format", "-show_streams", evidence_path],
                capture_output=True, text=True, timeout=30,
            )
            info = json.loads(proc.stdout)
        except Exception as e:
            return ParseResult(
                vendor=self.vendor_name, parser_version=self.parser_version,
                success=False, error_code=ParseError.PARSE_FAILED, errors=[str(e)],
            )

        video_stream = next((s for s in info.get("streams", []) if s.get("codec_type") == "video"), None)
        fmt = info.get("format", {})

        recording = NormalizedRecording(
            camera_id="CH-UNKNOWN",
            recording_id="generic-000000",
            source_path=evidence_path,
            extracted_path=evidence_path,
            original_timestamp=None,
            normalized_timestamp=None,
            duration_seconds=float(fmt.get("duration")) if fmt.get("duration") else None,
            resolution=f"{video_stream['width']}x{video_stream['height']}" if video_stream else None,
            fps=_parse_fps(video_stream["r_frame_rate"]) if video_stream else None,
            codec=video_stream.get("codec_name") if video_stream else None,
            file_size=int(fmt.get("size")) if fmt.get("size") else None,
            recovery_status="ORIGINAL",
            raw_metadata=info,
        )
        return ParseResult(
            vendor=self.vendor_name, parser_version=self.parser_version,
            success=True, recordings=[recording],
        )

    def extract_recordings(
        self, evidence_path: str, output_directory: str,
        recordings: list[NormalizedRecording], raw_master_block: object | None = None,
    ) -> ParseResult:
        return ParseResult(
            vendor=self.vendor_name,
            parser_version=self.parser_version,
            success=True,
            recordings=recordings,
            raw_master_block=raw_master_block,
        )