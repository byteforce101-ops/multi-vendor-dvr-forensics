"""
Dahua DVR/NVR raw disk image and .dav file parser.

Dahua uses two layers of proprietary format:
  1. DHFS (Dahua File System) — disk-level: identified by "DHFS4.1" at offset 0x00 of
     a raw disk image. The filesystem stores H.264/H.265 video in DHAV-framed streams,
     indexed by an internal channel/timestamp table.
  2. DHAV (Dahua Video) — stream/file-level: each frame starts with the 4-byte magic
     "DHAV" (0x44 0x48 0x41 0x56) or "DAHUA" (0x44 0x41 0x48 0x55 0x41), followed by
     a 20-byte header and optional extension blocks, closed by a "dhav" footer.

DHAV frame structure (per FFmpeg libavformat/dhav.c, Paul B Mahol, 2018):
  [0]    4B  magic    "DHAV" or "DAHUA"
  [4]    1B  type     0xf0=video I-frame, 0xf1=video P-frame, 0xfc/0xfd=audio
  [5]    1B  channel  camera channel ID (0-indexed)
  [6]    2B  subno    frame sub-number (LE uint16)
  [8]    4B  frameno  frame number (LE uint32)
  [12]   4B  date     BCD-style packed LE uint32:
                        bits [31:26] = year - 2000
                        bits [25:22] = month (1-12)
                        bits [21:17] = day (1-31)
                        bits [16:12] = hour (0-23)
                        bits [11:6]  = minute (0-59)
                        bits [5:0]   = second (0-59)
  [16]   4B  ts_ms    timestamp in milliseconds (LE uint32)
  [20]   4B  length   payload length in bytes, NOT counting header (24B) or footer (8B)
  [24]   NB  ext      extension blocks until payload
  ...    4B  footer   "dhav" (lowercase) + 4B back-offset to frame start

DHFS4.1 superblock signature (verified against Dahua forensic research):
  Offset 0x0000, 7 bytes: 0x44 0x48 0x46 0x53 0x34 0x2E 0x31 = ASCII "DHFS4.1"
"""

import logging
import mmap
import os
import shutil
import struct
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from backend.parsers.common.base import (
    BaseDVRParser,
    NormalizedRecording,
    ParseError,
    ParseResult,
)

logger = logging.getLogger(__name__)

# ── Signatures ──────────────────────────────────────────────────────────────
DHFS_SIGNATURE = b"DHFS4.1"          # disk-level superblock at offset 0
DHAV_MAGIC     = b"DHAV"             # frame-level magic (uppercase)
DAHUA_MAGIC    = b"DAHUA"            # alternate magic on some firmware
DHAV_FOOTER    = b"dhav"             # frame footer (lowercase)

# Valid DHAV frame types (from FFmpeg dhav_probe in libavformat/dhav.c):
# buf[4] must be one of 0xf0, 0xf1, 0xfc, 0xfd for probe to succeed
# Semantics per FFmpeg read_packet + research subagent report:
#   0xf0 = I-frame (keyframe / IDR)
#   0xf1 = Audio frame
#   0xfc = Config / metadata (SPS/PPS extension)
#   0xfd = Video P/B frame
DHAV_VIDEO_TYPES = {0xf0, 0xfd}      # keyframe and inter-frame
DHAV_AUDIO_TYPES = {0xf1}            # audio
DHAV_META_TYPES  = {0xfc}            # config/metadata
DHAV_ALL_TYPES   = DHAV_VIDEO_TYPES | DHAV_AUDIO_TYPES | DHAV_META_TYPES




# Minimum file sizes
_MIN_DAV_SIZE   = 32                  # at least one valid frame header
_MIN_DISK_SIZE  = 512                 # disk superblock needs 512 bytes

# Scan window for DHAV frames in large images
_SCAN_WINDOW    = 4 * 1024 * 1024    # 4 MB — enough to detect format


# ── Timestamp decoding ───────────────────────────────────────────────────────
def _decode_dhav_date(date_le: int) -> Optional[datetime]:
    """
    Decode the DHAV date field.

    Bit layout (from FFmpeg dhav.c, dhav_read_packet):
        year   = (date >> 26) + 2000
        month  = (date >> 22) & 0xF
        day    = (date >> 17) & 0x1F
        hour   = (date >> 12) & 0x1F
        minute = (date >>  6) & 0x3F
        second =  date        & 0x3F
    """
    try:
        year   = (date_le >> 26) + 2000
        month  = (date_le >> 22) & 0x0F
        day    = (date_le >> 17) & 0x1F
        hour   = (date_le >> 12) & 0x1F
        minute = (date_le >>  6) & 0x3F
        second =  date_le        & 0x3F

        if not (2000 <= year <= 2099 and 1 <= month <= 12 and 1 <= day <= 31):
            return None
        if hour > 23 or minute > 59 or second > 59:
            return None

        return datetime(year, month, day, hour, minute, second, tzinfo=timezone.utc)
    except (ValueError, OverflowError):
        return None


# ── Frame scanning ────────────────────────────────────────────────────────────
def _is_valid_dhav_frame_header(data: bytes, offset: int) -> bool:
    """Quick sanity check on a candidate DHAV frame header at `offset`."""
    if offset + 24 > len(data):
        return False
    magic = data[offset:offset + 4]
    if magic not in (DHAV_MAGIC, DAHUA_MAGIC):
        return False
    frame_type = data[offset + 4]
    if frame_type not in DHAV_ALL_TYPES:
        return False
    return True


def _scan_dhav_frames(data: bytes) -> list[dict]:
    """
    Scan a byte buffer for DHAV frame boundaries.
    Returns a list of frame dicts with keys:
        offset, channel, frame_type, timestamp, length
    """
    frames: list[dict] = []
    pos = 0
    data_len = len(data)

    while pos < data_len - 24:
        # Search for DHAV or DAHUA magic
        dhav_pos = data.find(DHAV_MAGIC, pos)
        dahua_pos = data.find(DAHUA_MAGIC, pos)

        if dhav_pos == -1 and dahua_pos == -1:
            break

        # Take whichever magic comes first
        if dhav_pos == -1:
            candidate = dahua_pos
        elif dahua_pos == -1:
            candidate = dhav_pos
        else:
            candidate = min(dhav_pos, dahua_pos)

        if candidate + 24 > data_len:
            break

        frame_type = data[candidate + 4]
        if frame_type not in DHAV_ALL_TYPES:
            pos = candidate + 1
            continue

        channel   = data[candidate + 5]
        date_raw  = struct.unpack_from("<I", data, candidate + 12)[0]
        ts_ms     = struct.unpack_from("<I", data, candidate + 16)[0]
        length    = struct.unpack_from("<I", data, candidate + 20)[0]
        timestamp = _decode_dhav_date(date_raw)

        frames.append({
            "offset":     candidate,
            "channel":    channel,
            "frame_type": frame_type,
            "timestamp":  timestamp,
            "length":     length,
            "ts_ms":      ts_ms,
        })

        # Jump past this frame (header + payload + footer)
        next_pos = candidate + 24 + length + 8
        pos = next_pos if next_pos > candidate + 1 else candidate + 1

    return frames


def _frames_to_recordings(
    frames: list[dict], evidence_path: str, vendor: str
) -> list[NormalizedRecording]:
    """
    Group scanned DHAV frames by channel into NormalizedRecordings.
    Each contiguous block of frames on the same channel = one recording.
    """
    if not frames:
        return []

    # Group by channel — keep channel order stable
    by_channel: dict[int, list[dict]] = {}
    for f in frames:
        ch = f["channel"]
        by_channel.setdefault(ch, []).append(f)

    recordings: list[NormalizedRecording] = []
    for ch, ch_frames in sorted(by_channel.items()):
        # Use the earliest valid timestamp
        valid_ts = [f["timestamp"] for f in ch_frames if f["timestamp"] is not None]
        start_ts = min(valid_ts) if valid_ts else None

        total_bytes = sum(f["length"] for f in ch_frames)
        rec_id = f"{vendor}-ch{ch:02d}-{len(recordings):04d}"

        recordings.append(NormalizedRecording(
            camera_id=f"CH-{ch:02d}",
            recording_id=rec_id,
            source_path=evidence_path,
            extracted_path=None,
            original_timestamp=start_ts,
            normalized_timestamp=start_ts,
            duration_seconds=None,          # calculated after extraction
            resolution=None,
            fps=None,
            codec="h264",                   # Dahua DVRs are predominantly H.264
            file_size=total_bytes,
            recovery_status="ORIGINAL",
            device_model="Dahua DVR/NVR",
            raw_metadata={
                "channel":       ch,
                "frame_count":   len(ch_frames),
                "first_offset":  ch_frames[0]["offset"],
                "last_offset":   ch_frames[-1]["offset"],
            },
        ))

    return recordings


# ── Extraction helpers ────────────────────────────────────────────────────────
def _run_ffmpeg(cmd: list[str]) -> tuple[int, str]:
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return p.returncode, p.stderr.decode("utf-8", "ignore")


def _extract_dav_to_mp4(
    input_path: str, output_path: str, channel_index: int = 0
) -> tuple[bool, str]:
    """
    Convert a .dav / raw DHAV stream to MP4 using FFmpeg's built-in DHAV demuxer.
    Tries stream copy first; falls back to re-encode.
    """
    # Stream copy (fastest, lossless)
    rc, err = _run_ffmpeg([
        "ffmpeg", "-y",
        "-f", "dhav",
        "-analyzeduration", "100M", "-probesize", "100M",
        "-i", input_path,
        "-map", f"0:v:{channel_index}",
        "-c:v", "copy",
        "-movflags", "+faststart",
        output_path,
    ])
    if rc == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
        return True, ""

    # Fallback: re-encode with libx264
    rc, err = _run_ffmpeg([
        "ffmpeg", "-y",
        "-f", "dhav",
        "-analyzeduration", "100M", "-probesize", "100M",
        "-fflags", "+genpts+discardcorrupt",
        "-i", input_path,
        "-map", f"0:v:{channel_index}",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        output_path,
    ])
    return (
        rc == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 0,
        err,
    )


def _probe_mp4(path: str) -> dict:
    """Probe an MP4 output for duration/resolution/fps via ffprobe."""
    if not shutil.which("ffprobe"):
        return {}
    cmd = [
        "ffprobe", "-v", "error",
        "-print_format", "json",
        "-show_format", "-show_streams",
        path,
    ]
    try:
        import json
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if proc.returncode != 0 or not proc.stdout.strip():
            return {}
        info = json.loads(proc.stdout)
        vs = next((s for s in info.get("streams", []) if s.get("codec_type") == "video"), None)
        fmt = info.get("format", {})
        result: dict = {}
        if fmt.get("duration"):
            result["duration_seconds"] = float(fmt["duration"])
        if vs:
            w, h = vs.get("width"), vs.get("height")
            if w and h:
                result["resolution"] = f"{w}x{h}"
            if vs.get("r_frame_rate"):
                try:
                    num, den = vs["r_frame_rate"].split("/")
                    result["fps"] = round(int(num) / int(den), 2) if int(den) else None
                except Exception:
                    pass
            result["codec"] = vs.get("codec_name", "h264")
        return result
    except Exception:
        return {}


# ── Parser class ──────────────────────────────────────────────────────────────
class DahuaParser(BaseDVRParser):
    """
    Parser for Dahua DVR/NVR evidence:
    - Raw disk images with DHFS4.1 superblock
    - .dav files containing DHAV frame streams
    """

    vendor_name    = "dahua"
    parser_version = "0.1.0"
    max_confidence = 0.90

    # ── detect ────────────────────────────────────────────────────────────────
    def detect(self, evidence_path: str) -> tuple[bool, float, dict]:
        try:
            p = Path(evidence_path)
            if not p.exists() or not p.is_file():
                return False, 0.0, {}

            size = p.stat().st_size
            if size < _MIN_DAV_SIZE:
                return False, 0.0, {}

            with open(p, "rb") as f:
                # Read first 7 bytes for DHFS4.1
                head = f.read(max(7, min(_SCAN_WINDOW, size)))

            # 1. DHFS4.1 disk superblock — highest confidence
            if head[:7] == DHFS_SIGNATURE:
                return True, 0.90, {
                    "vendor": "dahua",
                    "format": "dhfs_disk_image",
                    "signature": "DHFS4.1",
                }

            # 2. .dav file with DHAV/DAHUA magic at byte 0 — direct stream
            if p.suffix.lower() == ".dav":
                if head[:4] in (DHAV_MAGIC, DAHUA_MAGIC):
                    frame_type = head[4] if len(head) > 4 else 0
                    if frame_type in DHAV_ALL_TYPES:
                        return True, 0.85, {
                            "vendor": "dahua",
                            "format": "dav_stream",
                            "signature": head[:5].hex(),
                        }

            # 3. Scan first 4MB for DHAV frames (disk image without DHFS4.1)
            frames = _scan_dhav_frames(head[:_SCAN_WINDOW])
            if len(frames) >= 3:
                return True, 0.80, {
                    "vendor": "dahua",
                    "format": "dhav_stream_embedded",
                    "dhav_frames_found": len(frames),
                }

            return False, 0.0, {}

        except (OSError, struct.error, ValueError):
            return False, 0.0, {}

    # ── validate ──────────────────────────────────────────────────────────────
    def validate(self, evidence_path: str) -> tuple[bool, list[str]]:
        warnings: list[str] = []
        try:
            p = Path(evidence_path)
            if not p.exists():
                return False, ["Evidence file does not exist"]
            if p.stat().st_size < _MIN_DAV_SIZE:
                return False, ["Evidence file is too small to contain valid Dahua data"]

            with open(p, "rb") as f:
                head = f.read(min(_SCAN_WINDOW, p.stat().st_size))

            # DHFS4.1 presence check
            if head[:7] == DHFS_SIGNATURE:
                return True, warnings  # superblock intact

            # DHAV stream check
            if head[:4] in (DHAV_MAGIC, DAHUA_MAGIC):
                if head[4] not in DHAV_ALL_TYPES:
                    warnings.append("First frame type byte is unexpected; stream may be truncated or encrypted")
                return True, warnings

            # Scan for frames
            frames = _scan_dhav_frames(head)
            if frames:
                return True, warnings

            return False, ["No DHFS4.1 superblock or DHAV frames found in evidence file"]
        except Exception as e:
            return False, [f"Validation failed: {e}"]

    # ── parse ─────────────────────────────────────────────────────────────────
    def parse(self, evidence_path: str, output_directory: str) -> ParseResult:
        os.makedirs(output_directory, exist_ok=True)
        warnings: list[str] = []

        try:
            p = Path(evidence_path)
            size = p.stat().st_size

            with open(p, "rb") as f:
                # For large disk images, scan a representative window
                scan_size = min(size, 64 * 1024 * 1024)  # 64 MB scan
                data = f.read(scan_size)

            is_disk_image = data[:7] == DHFS_SIGNATURE

            if is_disk_image:
                warnings.append("DHFS4.1 disk image detected — scanning for DHAV frame index")

            frames = _scan_dhav_frames(data)

            if not frames:
                # For large disk images, scan entire file in chunks
                if size > len(data):
                    warnings.append(
                        f"No DHAV frames in first {scan_size // 1024 // 1024}MB; "
                        "performing full-disk scan (may take time)"
                    )
                    with open(p, "rb") as f:
                        chunk_size = 8 * 1024 * 1024
                        while True:
                            chunk = f.read(chunk_size)
                            if not chunk:
                                break
                            frames.extend(_scan_dhav_frames(chunk))
                            if len(frames) >= 1000:
                                warnings.append("Frame scan capped at 1000 frames")
                                break

            if not frames:
                return ParseResult(
                    vendor=self.vendor_name,
                    parser_version=self.parser_version,
                    success=False,
                    error_code=ParseError.PARSE_FAILED,
                    errors=["No DHAV frames found in evidence file"],
                )

            recordings = _frames_to_recordings(frames, evidence_path, self.vendor_name)

            return ParseResult(
                vendor=self.vendor_name,
                parser_version=self.parser_version,
                success=True,
                recordings=recordings,
                warnings=warnings,
                raw_master_block={
                    "format": "dhfs_disk_image" if is_disk_image else "dhav_stream",
                    "total_frames_scanned": len(frames),
                    "channels_found": sorted({f["channel"] for f in frames}),
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

    # ── extract_recordings ────────────────────────────────────────────────────
    def extract_recordings(
        self,
        evidence_path: str,
        output_directory: str,
        recordings: list[NormalizedRecording],
        raw_master_block: object,
    ) -> ParseResult:
        if not shutil.which("ffmpeg"):
            return ParseResult(
                vendor=self.vendor_name,
                parser_version=self.parser_version,
                success=False,
                error_code=ParseError.EXTRACTION_FAILED,
                errors=["ffmpeg not found on PATH — required for DHAV extraction"],
            )

        os.makedirs(output_directory, exist_ok=True)
        warnings: list[str] = []
        errors:   list[str] = []
        updated:  list[NormalizedRecording] = []

        # For disk images: carve each channel's raw DHAV data to a temp .dav, then remux.
        # For .dav files: feed directly to ffmpeg with -map 0:v:<channel_index>
        p = Path(evidence_path)
        is_dav_file = p.suffix.lower() == ".dav"

        if is_dav_file:
            # Direct extraction per channel stream index
            for idx, rec in enumerate(recordings):
                ch_label = rec.camera_id.replace("CH-", "")
                out_name  = f"{rec.recording_id}.mp4"
                out_path  = os.path.join(output_directory, out_name)
                success, err = _extract_dav_to_mp4(evidence_path, out_path, channel_index=idx)
                if success:
                    probe = _probe_mp4(out_path)
                    import dataclasses
                    updated.append(dataclasses.replace(
                        rec,
                        extracted_path=out_path,
                        recovery_status="RECOVERED",
                        duration_seconds=probe.get("duration_seconds"),
                        resolution=probe.get("resolution"),
                        fps=probe.get("fps"),
                        codec=probe.get("codec", rec.codec),
                    ))
                else:
                    warnings.append(f"{rec.recording_id}: extraction failed — {err.strip()[-200:]}")
                    updated.append(rec)
        else:
            # Disk image: carve raw DHAV bytes per channel, write to temp .dav, extract
            try:
                with open(evidence_path, "rb") as f:
                    with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
                        data = bytes(mm[:min(len(mm), 64 * 1024 * 1024)])
            except Exception as e:
                return ParseResult(
                    vendor=self.vendor_name, parser_version=self.parser_version,
                    success=False, error_code=ParseError.EXTRACTION_FAILED,
                    errors=[f"Could not read evidence file for extraction: {e}"],
                )

            all_frames = _scan_dhav_frames(data)
            by_channel: dict[int, list[dict]] = {}
            for fr in all_frames:
                by_channel.setdefault(fr["channel"], []).append(fr)

            for rec in recordings:
                ch_num = int(rec.camera_id.replace("CH-", "").lstrip("0") or "0")
                ch_frames = by_channel.get(ch_num, [])
                if not ch_frames:
                    warnings.append(f"{rec.recording_id}: no frames found for channel {ch_num}")
                    updated.append(rec)
                    continue

                # Extract raw DHAV bytes for this channel
                carved_bytes = bytearray()
                for fr in ch_frames:
                    end = fr["offset"] + 24 + fr["length"] + 8
                    if end <= len(data):
                        carved_bytes.extend(data[fr["offset"]:end])

                if not carved_bytes:
                    warnings.append(f"{rec.recording_id}: carved data is empty")
                    updated.append(rec)
                    continue

                fd, tmp_dav = tempfile.mkstemp(suffix=".dav")
                try:
                    with os.fdopen(fd, "wb") as tf:
                        tf.write(carved_bytes)

                    out_path = os.path.join(output_directory, f"{rec.recording_id}.mp4")
                    success, err = _extract_dav_to_mp4(tmp_dav, out_path, channel_index=0)
                    if success:
                        probe = _probe_mp4(out_path)
                        import dataclasses
                        updated.append(dataclasses.replace(
                            rec,
                            extracted_path=out_path,
                            recovery_status="RECOVERED",
                            duration_seconds=probe.get("duration_seconds"),
                            resolution=probe.get("resolution"),
                            fps=probe.get("fps"),
                            codec=probe.get("codec", rec.codec),
                        ))
                    else:
                        errors.append(f"{rec.recording_id}: extraction failed — {err.strip()[-200:]}")
                        updated.append(rec)
                finally:
                    if os.path.exists(tmp_dav):
                        os.remove(tmp_dav)

        return ParseResult(
            vendor=self.vendor_name,
            parser_version=self.parser_version,
            success=len(errors) == 0,
            recordings=updated,
            warnings=warnings,
            errors=errors,
            error_code=ParseError.PARTIALLY_PARSED if errors else None,
        )
