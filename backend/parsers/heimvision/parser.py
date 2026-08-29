import os
import json
import hashlib
import subprocess
from pathlib import Path

from backend.parsers.common.base import (
    BaseDVRParser,
    ParseResult,
    ParseError,
    NormalizedRecording,
)


VPS_MARKER = b"\x00\x00\x00\x01\x40"
MARKER_LEN = len(VPS_MARKER)


def sha256_file(filepath):
    sha256 = hashlib.sha256()

    with open(filepath, "rb") as f:
        while True:
            chunk = f.read(1024 * 1024)

            if not chunk:
                break

            sha256.update(chunk)

    return sha256.hexdigest()


def find_markers_streaming(filepath, chunk_size=64 * 1024 * 1024, max_offsets=None):
    """
    Scans a file for VPS_MARKER without loading it fully into memory.
    Keeps a small overlap buffer between chunks so a marker split across
    a chunk boundary is never missed.
    """
    offsets = []
    overlap = MARKER_LEN - 1
    carry = b""
    absolute_pos = 0

    with open(filepath, "rb") as f:
        while True:
            chunk = f.read(chunk_size)

            if not chunk:
                break

            search_data = carry + chunk
            search_base = absolute_pos - len(carry)

            start = 0

            while True:
                position = search_data.find(VPS_MARKER, start)

                if position == -1:
                    break

                offset = search_base + position

                if not offsets or offset != offsets[-1]:
                    offsets.append(offset)

                start = position + 1

                if max_offsets and len(offsets) >= max_offsets:
                    return offsets

            carry = chunk[-overlap:] if len(chunk) >= overlap else search_data[-overlap:]
            absolute_pos += len(chunk)

    return offsets


def find_markers_in_sample(sample):
    offsets = []
    start = 0

    while True:
        position = sample.find(VPS_MARKER, start)

        if position == -1:
            break

        offsets.append(position)
        start = position + 1

    return offsets


def probe_hevc(filepath):
    command = [
        "ffprobe",
        "-v", "error",
        "-f", "hevc",
        "-show_entries",
        "stream=codec_name,width,height,r_frame_rate",
        "-of",
        "json",
        str(filepath),
    ]

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=30,
        )

        data = json.loads(result.stdout)
        streams = data.get("streams", [])

        if not streams:
            return {
                "valid": False,
                "codec": None,
                "width": None,
                "height": None,
                "fps": None,
            }

        stream = streams[0]

        width = stream.get("width")
        height = stream.get("height")

        return {
            "valid": bool(width and height),
            "codec": stream.get("codec_name"),
            "width": width,
            "height": height,
            "fps": stream.get("r_frame_rate"),
        }

    except Exception:
        return {
            "valid": False,
            "codec": None,
            "width": None,
            "height": None,
            "fps": None,
        }


def check_decode(filepath):
    command = [
        "ffmpeg",
        "-v", "error",
        "-f", "hevc",
        "-i", str(filepath),
        "-frames:v", "1",
        "-f", "null",
        "-",
    ]

    try:
        result = subprocess.run(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=30,
        )

        return result.returncode == 0

    except Exception:
        return False


def remux_to_mp4(input_file, output_file):
    command = [
        "ffmpeg",
        "-y",
        "-v", "error",
        "-f", "hevc",
        "-i", str(input_file),
        "-c", "copy",
        str(output_file),
    ]

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=60,
        )

        return (
            result.returncode == 0
            and output_file.exists()
            and output_file.stat().st_size > 0
        )

    except Exception:
        return False


def extract_segment_to_disk(source_path, start_offset, end_offset, dest_path, chunk_size=8 * 1024 * 1024):
    """
    Copies a byte range [start_offset, end_offset) from source_path to
    dest_path without reading the whole source file into memory.
    """
    remaining = end_offset - start_offset

    with open(source_path, "rb") as src, open(dest_path, "wb") as dst:
        src.seek(start_offset)

        while remaining > 0:
            read_size = min(chunk_size, remaining)
            chunk = src.read(read_size)

            if not chunk:
                break

            dst.write(chunk)
            remaining -= len(chunk)


class HeimVisionParser(BaseDVRParser):
    vendor_name = "heimvision"
    parser_version = "0.2.0"

    def detect(self, evidence_path):
        try:
            path = Path(evidence_path)

            if not path.exists() or not path.is_file():
                return False, 0.0, {}

            with open(path, "rb") as f:
                sample = f.read(8 * 1024 * 1024)

            markers = find_markers_in_sample(sample)

            if len(markers) >= 2:
                confidence = 0.75

                if path.suffix.lower() in [".dat", ".bin", ".img"]:
                    confidence = 0.85

                return True, confidence, {
                    "vendor": "heimvision",
                    "format": "raw_hevc",
                    "vps_markers_found_in_sample": len(markers),
                }

            return False, 0.0, {}

        except Exception:
            return False, 0.0, {}

    def validate(self, evidence_path):
        warnings = []

        try:
            path = Path(evidence_path)

            if not path.exists():
                return False, ["Evidence file does not exist"]

            if path.stat().st_size == 0:
                return False, ["Evidence file is empty"]

            with open(path, "rb") as f:
                sample = f.read(8 * 1024 * 1024)

            markers = find_markers_in_sample(sample)

            if not markers:
                return False, [
                    "No HEVC VPS markers found in evidence sample"
                ]

            if len(markers) < 2:
                warnings.append(
                    "Only one HEVC VPS marker found in the first 8MB; "
                    "extraction may be incomplete or the file may be larger "
                    "than the sample scanned"
                )

            return True, warnings

        except Exception as e:
            return False, [f"Validation failed: {e}"]

    def parse(self, evidence_path, output_directory):
        warnings = []
        recordings = []

        try:
            input_file = Path(evidence_path)
            output_dir = Path(output_directory)

            output_dir.mkdir(
                parents=True,
                exist_ok=True,
            )

            file_size = input_file.stat().st_size
            markers = find_markers_streaming(input_file)

            if not markers:
                return ParseResult(
                    vendor=self.vendor_name,
                    parser_version=self.parser_version,
                    success=False,
                    error_code=ParseError.PARSE_FAILED,
                    errors=["No HEVC VPS markers found"],
                )

            manifest_segments = []

            for i, start_offset in enumerate(markers):

                if i + 1 < len(markers):
                    end_offset = markers[i + 1]
                else:
                    end_offset = file_size

                segment_size = end_offset - start_offset

                segment_name = f"segment_{i:04d}.h265"
                segment_path = output_dir / segment_name

                extract_segment_to_disk(
                    input_file,
                    start_offset,
                    end_offset,
                    segment_path,
                )

                metadata = probe_hevc(segment_path)
                independently_decodable = check_decode(segment_path)

                if independently_decodable:
                    recovery_status = "RECOVERED"
                    decode_status = "SUCCESS"
                elif metadata["codec"] == "hevc":
                    recovery_status = "PARTIAL"
                    decode_status = "CONTEXT_DEPENDENT"
                    warnings.append(
                        f"{segment_name}: HEVC stream detected but cannot "
                        f"be independently decoded"
                    )
                else:
                    recovery_status = "PARTIAL"
                    decode_status = "FAILED"
                    warnings.append(
                        f"{segment_name}: invalid or incomplete HEVC segment"
                    )

                resolution = None

                if metadata["width"] and metadata["height"]:
                    resolution = (
                        f"{metadata['width']}x{metadata['height']}"
                    )

                segment_hash = sha256_file(segment_path)

                recording = NormalizedRecording(
                    camera_id="UNKNOWN",
                    recording_id=f"heimvision-{i:06d}",
                    source_path=str(input_file),
                    extracted_path=str(segment_path),
                    original_timestamp=None,
                    normalized_timestamp=None,
                    duration_seconds=None,
                    resolution=resolution,
                    fps=None,
                    codec=metadata["codec"],
                    file_size=segment_size,
                    recovery_status=recovery_status,
                    device_model="HeimVision",
                    raw_metadata={
                        "segment_id": i,
                        "start_offset": start_offset,
                        "end_offset": end_offset,
                        "sha256": segment_hash,
                        "decode_status": decode_status,
                    },
                )

                recordings.append(recording)

                manifest_segments.append({
                    "segment_id": i,
                    "filename": segment_name,
                    "start_offset": start_offset,
                    "end_offset": end_offset,
                    "size_bytes": segment_size,
                    "sha256": segment_hash,
                    "codec": metadata["codec"],
                    "width": metadata["width"],
                    "height": metadata["height"],
                    "decode_status": decode_status,
                    "recovery_status": recovery_status,
                })

            manifest = {
                "vendor": "heimvision",
                "source_file": str(input_file),
                "source_size": file_size,
                "segment_count": len(recordings),
                "segments": manifest_segments,
            }

            manifest_path = output_dir / "manifest.json"

            with open(
                manifest_path,
                "w",
                encoding="utf-8",
            ) as f:
                json.dump(manifest, f, indent=4)

            return ParseResult(
                vendor=self.vendor_name,
                parser_version=self.parser_version,
                success=True,
                recordings=recordings,
                warnings=warnings,
                raw_master_block={
                    "source_size": file_size,
                    "segment_count": len(recordings),
                    "manifest": str(manifest_path),
                },
            )

        except Exception as e:
            return ParseResult(
                vendor=self.vendor_name,
                parser_version=self.parser_version,
                success=False,
                error_code=ParseError.PARSE_FAILED,
                errors=[str(e)],
            )

    def extract_recordings(
        self,
        evidence_path,
        output_directory,
        recordings,
        raw_master_block,
    ):
        output_dir = Path(output_directory)
        output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        updated = []
        warnings = []
        errors = []

        for recording in recordings:

            if not recording.extracted_path:
                updated.append(recording)
                continue

            input_path = Path(recording.extracted_path)

            if not input_path.exists():
                warnings.append(
                    f"{recording.recording_id}: extracted segment missing"
                )
                updated.append(recording)
                continue

            if not recording.raw_metadata or recording.raw_metadata.get("decode_status") != "SUCCESS":
                updated.append(recording)
                continue

            output_path = (
                output_dir /
                f"{recording.recording_id}.mp4"
            )

            success = remux_to_mp4(
                input_path,
                output_path,
            )

            if success:
                recording.extracted_path = str(output_path)
            else:
                errors.append(
                    f"{recording.recording_id}: MP4 remux failed"
                )

            updated.append(recording)

        return ParseResult(
            vendor=self.vendor_name,
            parser_version=self.parser_version,
            success=len(errors) == 0,
            recordings=updated,
            warnings=warnings,
            errors=errors,
            error_code=(
                ParseError.PARTIALLY_PARSED
                if errors
                else None
            ),
            raw_master_block=raw_master_block,
        )