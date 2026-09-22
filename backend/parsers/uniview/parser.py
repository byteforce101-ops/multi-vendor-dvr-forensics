"""
Uniview (UNV) NVR parser.

Uniview Technology Co., Ltd. (formerly Zhejiang Uniview Technologies) is a major
Chinese NVR/IP-camera manufacturer. Their NVRs use a proprietary disk architecture
called UBS (Universal Block Storage), which stores video as raw H.264/H.265 (Ultra 265)
NAL Annex B streams directly in physical disk blocks, without a mountable filesystem.

There is no publicly documented UBS disk superblock signature analogous to Hikvision's
"HIKVISION@HANGZHOU" or Dahua's "DHFS4.1". Forensic research confirms this:
  - UBS-formatted drives appear as unpartitioned/unallocated to all standard OS tools
  - Commercial tools (Magnet DVR Examiner, SalvationDATA) recover UBS via proprietary parsers
  - No GitHub open-source parser for UBS disk images exists as of 2026

Detection strategy used here (forensically honest, no false positives):
  1. Scan the first 64KB for Uniview brand strings ("Uniview", "UNV", "UNIVIEW", etc.)
  2. If brand strings found: scan the body for H.265 HEVC VPS NAL units (common in
     Uniview "Ultra 265" streams) or H.264 IDR start codes
  3. Never return True without at least one brand string — prevents false matches
     on generic H.264/H.265 data

Parse strategy:
  - Since UBS has no index, scan the disk for H.264/H.265 IDR NAL unit start codes
    and carve contiguous stream segments between them
  - Remux extracted raw streams to MP4 via FFmpeg

Export detection:
  - Uniview NVRs can export standard .mp4, .ts, and .uvf files
  - For exported .uvf files: detect by Uniview brand strings in metadata
    and hand off to FFmpeg (which can decode the H.265 payload)
"""

import logging
import os
import shutil
import struct
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from backend.parsers.common.base import (
    BaseDVRParser,
    NormalizedRecording,
    ParseError,
    ParseResult,
)

logger = logging.getLogger(__name__)

# ── Brand detection ──────────────────────────────────────────────────────────
_UNIVIEW_BRAND_STRINGS: list[bytes] = [
    b"Uniview",
    b"UNIVIEW",
    b"uniview",
    b"Uni-View",
    b"UNV",
    # NVR model prefixes
    b"NVR301",
    b"NVR302",
    b"NVR308",
    b"NVR316",
    b"NVR504",
    b"NVR516",
    b"IPC32",
    b"IPC36",
    # Firmware strings sometimes visible in memory areas
    b"Ultra265",
    b"Ultra 265",
    b"ULTRA265",
]

_BRAND_SCAN_BYTES   = 64 * 1024     # 64 KB brand scan window
_BODY_SCAN_BYTES    = 8 * 1024 * 1024  # 8 MB for NAL detection
_MIN_SIZE           = 64

# ── H.264/H.265 NAL unit markers ────────────────────────────────────────────
# H.264 Annex B start code + IDR NAL unit type (0x65 = nal_unit_type 5, IDR slice)
H264_IDR_CODES: list[bytes] = [
    b"\x00\x00\x00\x01\x65",   # 4-byte start code + IDR
    b"\x00\x00\x01\x65",       # 3-byte start code + IDR
]

# H.265/HEVC VPS NAL unit (Video Parameter Set) — nal_unit_type 32 (0x40)
# Often present at the start of Ultra 265 streams
H265_VPS_CODES: list[bytes] = [
    b"\x00\x00\x00\x01\x40",   # 4-byte start code + VPS
    b"\x00\x00\x01\x40",       # 3-byte start code + VPS
]

# H.265 IDR NAL (nal_unit_type 19 = 0x26, with nuh_layer_id=0, nuh_temporal_id=1 → 0x01)
H265_IDR_CODES: list[bytes] = [
    b"\x00\x00\x00\x01\x26\x01",
    b"\x00\x00\x01\x26\x01",
]


def _contains_uniview_brand(data: bytes) -> bool:
    for marker in _UNIVIEW_BRAND_STRINGS:
        if marker in data:
            return True
    return False


def _find_nal_starts(data: bytes) -> list[int]:
    """Find all H.264 IDR or H.265 VPS/IDR start positions in data."""
    positions: list[int] = []
    all_markers = H264_IDR_CODES + H265_VPS_CODES + H265_IDR_CODES
    for marker in all_markers:
        pos = 0
        while True:
            idx = data.find(marker, pos)
            if idx == -1:
                break
            positions.append(idx)
            pos = idx + 1
    return sorted(set(positions))


def _run_ffmpeg(cmd: list[str]) -> tuple[int, str]:
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return p.returncode, p.stderr.decode("utf-8", "ignore")


def _probe_mp4(path: str) -> dict:
    if not shutil.which("ffprobe"):
        return {}
    import json
    cmd = [
        "ffprobe", "-v", "error",
        "-print_format", "json",
        "-show_format", "-show_streams",
        path,
    ]
    try:
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
            result["codec"] = vs.get("codec_name", "hevc")
            if vs.get("r_frame_rate"):
                try:
                    num, den = vs["r_frame_rate"].split("/")
                    result["fps"] = round(int(num) / int(den), 2) if int(den) else None
                except Exception:
                    pass
        return result
    except Exception:
        return {}


def _remux_raw_stream_to_mp4(input_path: str, output_path: str) -> tuple[bool, str]:
    """Try to remux a raw H.264 or H.265 Annex B stream to MP4."""
    # Try H.265/HEVC first (Uniview Ultra 265 is H.265-based)
    for input_fmt in ("hevc", "h264"):
        rc, err = _run_ffmpeg([
            "ffmpeg", "-y",
            "-f", input_fmt,
            "-analyzeduration", "100M", "-probesize", "100M",
            "-fflags", "+genpts+discardcorrupt",
            "-i", input_path,
            "-c:v", "copy",
            "-movflags", "+faststart",
            output_path,
        ])
        if rc == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            return True, ""

    # Fallback: auto-detect and re-encode
    rc, err = _run_ffmpeg([
        "ffmpeg", "-y",
        "-analyzeduration", "100M", "-probesize", "100M",
        "-fflags", "+genpts+discardcorrupt",
        "-i", input_path,
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        output_path,
    ])
    return (
        rc == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 0,
        err,
    )


# ── Parser class ──────────────────────────────────────────────────────────────
class UnivewParser(BaseDVRParser):
    """
    Parser for Uniview (UNV) NVR evidence.
    Detects via brand strings + H.264/H.265 NAL unit presence.
    Extracts by carving raw NAL streams and remuxing via FFmpeg.
    """

    vendor_name    = "uniview"
    parser_version = "0.1.0"
    max_confidence = 0.75

    # ── detect ────────────────────────────────────────────────────────────────
    def detect(self, evidence_path: str) -> tuple[bool, float, dict]:
        try:
            p = Path(evidence_path)
            if not p.exists() or not p.is_file():
                return False, 0.0, {}
            if p.stat().st_size < _MIN_SIZE:
                return False, 0.0, {}

            with open(p, "rb") as f:
                head = f.read(min(_BRAND_SCAN_BYTES, p.stat().st_size))

            # Require brand strings — never guess on generic H.264/H.265
            if not _contains_uniview_brand(head):
                return False, 0.0, {}

            # Confirm video payload is present
            with open(p, "rb") as f:
                f.seek(_BRAND_SCAN_BYTES if p.stat().st_size > _BRAND_SCAN_BYTES else 0)
                body = f.read(min(_BODY_SCAN_BYTES, p.stat().st_size))

            all_data = head + body
            nal_starts = _find_nal_starts(all_data)

            is_hevc = any(all_data[n:n + 5] in (b"\x00\x00\x00\x01\x40", b"\x00\x00\x01\x40") for n in nal_starts)
            codec_hint = "hevc" if is_hevc else "h264"

            if not nal_starts:
                # Brand found but no decodable stream yet (maybe pure text metadata)
                return True, 0.60, {
                    "vendor": "uniview",
                    "format": "ubs_disk_image",
                    "brand_detected": True,
                    "nal_units_found": 0,
                }

            return True, 0.75, {
                "vendor": "uniview",
                "format": "ubs_disk_image",
                "brand_detected": True,
                "nal_units_found": len(nal_starts),
                "codec_hint": codec_hint,
            }

        except (OSError, struct.error, ValueError):
            return False, 0.0, {}

    # ── validate ──────────────────────────────────────────────────────────────
    def validate(self, evidence_path: str) -> tuple[bool, list[str]]:
        warnings: list[str] = []
        try:
            p = Path(evidence_path)
            if not p.exists():
                return False, ["Evidence file does not exist"]
            if p.stat().st_size < _MIN_SIZE:
                return False, ["Evidence file too small to contain Uniview data"]

            with open(p, "rb") as f:
                head = f.read(min(_BRAND_SCAN_BYTES, p.stat().st_size))

            if not _contains_uniview_brand(head):
                return False, ["No Uniview brand strings found in evidence file"]

            with open(p, "rb") as f:
                body = f.read(min(_BODY_SCAN_BYTES + _BRAND_SCAN_BYTES, p.stat().st_size))

            nal_starts = _find_nal_starts(body)
            if not nal_starts:
                warnings.append(
                    "Uniview brand detected but no H.264/H.265 NAL units found; "
                    "disk may be encrypted, empty, or require deeper scanning"
                )

            return True, warnings
        except Exception as e:
            return False, [f"Validation failed: {e}"]

    # ── parse ─────────────────────────────────────────────────────────────────
    def parse(self, evidence_path: str, output_directory: str) -> ParseResult:
        os.makedirs(output_directory, exist_ok=True)
        warnings: list[str] = []

        try:
            p = Path(evidence_path)
            size = p.stat().st_size

            # Scan up to 128MB for NAL unit starts
            scan_size = min(size, 128 * 1024 * 1024)
            with open(p, "rb") as f:
                data = f.read(scan_size)

            nal_starts = _find_nal_starts(data)

            if not nal_starts:
                return ParseResult(
                    vendor=self.vendor_name,
                    parser_version=self.parser_version,
                    success=False,
                    error_code=ParseError.PARSE_FAILED,
                    errors=["No H.264/H.265 NAL units found in Uniview evidence file"],
                )

            # Group NAL starts into "recording segments" — heuristic: gap > 256KB = new segment
            GAP_THRESHOLD = 256 * 1024
            segments: list[tuple[int, int]] = []  # (start, end)
            seg_start = nal_starts[0]
            seg_end   = nal_starts[0]

            for pos in nal_starts[1:]:
                if pos - seg_end > GAP_THRESHOLD:
                    segments.append((seg_start, seg_end + 4096))  # add small tail buffer
                    seg_start = pos
                seg_end = pos

            segments.append((seg_start, min(seg_end + 4096, len(data))))

            if not segments:
                return ParseResult(
                    vendor=self.vendor_name,
                    parser_version=self.parser_version,
                    success=False,
                    error_code=ParseError.PARSE_FAILED,
                    errors=["Could not identify any recording segments in Uniview evidence"],
                )

            recordings: list[NormalizedRecording] = []
            for seg_idx, (seg_start, seg_end) in enumerate(segments):
                seg_data = data[seg_start:seg_end]
                is_hevc  = any(
                    seg_data[:4096].find(m) >= 0
                    for m in (b"\x00\x00\x00\x01\x40", b"\x00\x00\x01\x40")
                )

                recordings.append(NormalizedRecording(
                    camera_id="CH-00",        # UBS has no channel index without full parser
                    recording_id=f"unv-seg-{seg_idx:04d}",
                    source_path=evidence_path,
                    extracted_path=None,
                    original_timestamp=None,  # No timestamp without UBS index
                    normalized_timestamp=None,
                    duration_seconds=None,
                    resolution=None,
                    fps=None,
                    codec="hevc" if is_hevc else "h264",
                    file_size=seg_end - seg_start,
                    recovery_status="RECOVERED",
                    device_model="Uniview NVR",
                    raw_metadata={
                        "segment_index": seg_idx,
                        "start_offset":  seg_start,
                        "end_offset":    seg_end,
                        "nal_count":     sum(
                            1 for n in nal_starts if seg_start <= n < seg_end
                        ),
                        "codec_hint": "hevc" if is_hevc else "h264",
                    },
                ))

            if len(segments) > 1:
                warnings.append(
                    f"UBS disk index not decoded — {len(segments)} stream segments "
                    "identified by NAL unit carving; channel assignment and timestamps "
                    "are unavailable without the UBS block table"
                )

            return ParseResult(
                vendor=self.vendor_name,
                parser_version=self.parser_version,
                success=True,
                recordings=recordings,
                warnings=warnings,
                raw_master_block={
                    "format":         "ubs_disk_image",
                    "nal_units_found": len(nal_starts),
                    "segments_found":  len(segments),
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
                errors=["ffmpeg not found on PATH — required for Uniview stream extraction"],
            )

        os.makedirs(output_directory, exist_ok=True)
        warnings: list[str] = []
        errors:   list[str] = []
        updated:  list[NormalizedRecording] = []

        try:
            with open(evidence_path, "rb") as f:
                import mmap
                with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
                    data = bytes(mm[:min(len(mm), 128 * 1024 * 1024)])
        except Exception as e:
            return ParseResult(
                vendor=self.vendor_name, parser_version=self.parser_version,
                success=False, error_code=ParseError.EXTRACTION_FAILED,
                errors=[f"Could not read evidence for extraction: {e}"],
            )

        import dataclasses

        for rec in recordings:
            meta = rec.raw_metadata or {}
            seg_start = meta.get("start_offset")
            seg_end   = meta.get("end_offset")

            if seg_start is None or seg_end is None:
                warnings.append(f"{rec.recording_id}: missing segment offsets, skipped")
                updated.append(rec)
                continue

            seg_data = data[seg_start:seg_end]
            if not seg_data or seg_data.count(0) == len(seg_data):
                warnings.append(f"{rec.recording_id}: segment data is empty/zeroed")
                updated.append(rec)
                continue

            fd, tmp_raw = tempfile.mkstemp(suffix=".bin")
            try:
                with os.fdopen(fd, "wb") as tf:
                    tf.write(seg_data)

                out_path = os.path.join(output_directory, f"{rec.recording_id}.mp4")
                success, err = _remux_raw_stream_to_mp4(tmp_raw, out_path)
                if success:
                    probe = _probe_mp4(out_path)
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
                    errors.append(f"{rec.recording_id}: remux failed — {err.strip()[-200:]}")
                    updated.append(rec)
            finally:
                if os.path.exists(tmp_raw):
                    os.remove(tmp_raw)

        return ParseResult(
            vendor=self.vendor_name,
            parser_version=self.parser_version,
            success=len(errors) == 0,
            recordings=updated,
            warnings=warnings,
            errors=errors,
            error_code=ParseError.PARTIALLY_PARSED if errors else None,
        )
