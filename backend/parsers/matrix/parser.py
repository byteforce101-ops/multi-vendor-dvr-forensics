"""
Matrix Comsec (SATATYA) DVR/NVR parser.

Matrix Comsec Pvt. Ltd. — headquartered in Vadodara, Gujarat, India — is an
authentic indigenous Indian manufacturer ("Make in India"). Unlike CP Plus,
Godrej, and Honeywell mid-range lines, Matrix is NOT an OEM of Dahua, Hikvision,
Xiongmai, or any other foreign surveillance ODM.

Matrix's surveillance product line is branded SATATYA (Sanskrit: "truth / reality"):
  - SATATYA NVR (SATATYA NVR0404P, NVR0801, NVR1601P, etc.)
  - SATATYA HVR (Hybrid Video Recorder)
  - SATATYA SAMAS (Server-based VMS)
  - SATATYA SIGHT (Recording module)
  - SATATYA CORE  (Enterprise NVR)

INTERNAL STORAGE ARCHITECTURE:
  Matrix initializes internal drives via SATATYA Local UI or Device Client.
  It uses a circular indexed block pool on proprietary embedded Linux,
  managed by the SATATYA daemon. The disk is NOT mountable by standard OS tools.
  RAID 0/1/5/6/10/50/60 supported on enterprise SATATYA CORE models.

PROPRIETARY FILE FORMATS (export/recording):
  .stm  — SATATYA Media (primary native stream container)
          Encapsulates raw H.264/H.265 NAL streams with Matrix sync metadata,
          channel IDs, and microsecond timestamps. Playable in Matrix Device Player only.
  .avs  — Backup stream format from MATRIX DVR Backup Manager
  .mxs  — Local recording from Device Client / Web Client / SATATYA CORE
  .avi  — Transcoded output from Matrix Device Player (H.264 payload)

BRAND STRINGS (visible in disk metadata, firmware, config files):
  "MATRIX", "Matrix Comsec", "MATRIX COMSEC PVT. LTD.", "SATATYA",
  "SATATYA NVR", "SATATYA SAMAS", "SATATYA SIGHT", "SATATYA CORE",
  "matrixcomsec.com"

NETWORK FINGERPRINT (for disk metadata / config identification):
  Default management port: 8000 (proprietary Matrix protocol)
  HTTP: 80, Camera forwarding: 8081
  RTSP: 554
  Default IPs: 192.168.1.123, 192.168.2.2

DETECTION STRATEGY:
  1. File extension: .stm / .mxs / .avs → check brand strings too
  2. Scan first 64 KB for SATATYA / Matrix brand strings
  3. If brand strings found: scan for H.264/H.265 NAL units
  4. If brand strings + NAL → high confidence; brand-only → lower confidence

EXTRACTION STRATEGY:
  - .stm / .mxs: FFmpeg can often demux these as raw H.264/H.265 (they carry
    Annex B NAL units inside); try -f h264 or -f hevc, then fallback to auto-detect
  - .avs: try FFmpeg auto-detect (has MP4/AVI-like structure in many firmware versions)
  - Raw disk: NAL carving between Matrix sync metadata markers

Source: Matrix Comsec product documentation, SATATYA system architecture guides,
        SIH 2026 Problem Statement SIH26150 forensic standardization requirement.
"""

import logging
import os
import shutil
import struct
import subprocess
import tempfile
from pathlib import Path

from backend.parsers.common.base import (
    BaseDVRParser,
    NormalizedRecording,
    ParseError,
    ParseResult,
)

logger = logging.getLogger(__name__)

# ── Brand strings ─────────────────────────────────────────────────────────────
MATRIX_BRAND_STRINGS: list[bytes] = [
    b"MATRIX",
    b"Matrix Comsec",
    b"MATRIX COMSEC",
    b"MATRIX COMSEC PVT",
    b"SATATYA",
    b"satatya",
    b"SATATYA NVR",
    b"SATATYA HVR",
    b"SATATYA SAMAS",
    b"SATATYA SIGHT",
    b"SATATYA CORE",
    b"matrixcomsec.com",
    b"MatrixComsec",
]

# Native Matrix extensions
MATRIX_EXTS = {".stm", ".mxs", ".avs"}

# H.264 / H.265 NAL Annex B start codes for stream carving
H264_IDR = b"\x00\x00\x00\x01\x65"   # H.264 IDR slice
H265_VPS = b"\x00\x00\x00\x01\x40"   # H.265 VPS
H264_SPS = b"\x00\x00\x00\x01\x67"   # H.264 SPS

_BRAND_SCAN_BYTES = 64 * 1024
_NAL_SCAN_BYTES   = 16 * 1024 * 1024
_MIN_SIZE         = 32


def _contains_matrix_brand(data: bytes) -> bool:
    lower = data.lower()
    for marker in MATRIX_BRAND_STRINGS:
        if marker.lower() in lower:
            return True
    return False


def _find_nal_starts(data: bytes) -> list[int]:
    """Find H.264 IDR, SPS, or H.265 VPS start positions."""
    positions: list[int] = []
    for marker in (H264_IDR, H265_VPS, H264_SPS):
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
    cmd = ["ffprobe", "-v", "error", "-print_format", "json",
           "-show_format", "-show_streams", path]
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
            result["codec"] = vs.get("codec_name", "h264")
            if vs.get("r_frame_rate"):
                try:
                    num, den = vs["r_frame_rate"].split("/")
                    result["fps"] = round(int(num) / int(den), 2) if int(den) else None
                except Exception:
                    pass
        return result
    except Exception:
        return {}


def _try_ffmpeg_extract(input_path: str, output_path: str) -> tuple[bool, str]:
    """
    Try multiple FFmpeg demux strategies for Matrix .stm / .mxs / .avs files.
    Strategy order:
      1. Auto-detect (works for .avs if it has MP4/AVI structure)
      2. Raw H.264 Annex B
      3. Raw H.265/HEVC Annex B
      4. Re-encode fallback
    """
    strategies = [
        # Auto-detect
        ["ffmpeg", "-y",
         "-analyzeduration", "100M", "-probesize", "100M",
         "-fflags", "+genpts+discardcorrupt",
         "-i", input_path,
         "-c:v", "copy", "-movflags", "+faststart", output_path],
        # Raw H.264
        ["ffmpeg", "-y", "-f", "h264",
         "-analyzeduration", "50M", "-probesize", "50M",
         "-fflags", "+genpts+discardcorrupt",
         "-i", input_path,
         "-c:v", "copy", "-movflags", "+faststart", output_path],
        # Raw H.265
        ["ffmpeg", "-y", "-f", "hevc",
         "-analyzeduration", "50M", "-probesize", "50M",
         "-fflags", "+genpts+discardcorrupt",
         "-i", input_path,
         "-c:v", "copy", "-movflags", "+faststart", output_path],
        # Re-encode fallback
        ["ffmpeg", "-y",
         "-fflags", "+genpts+discardcorrupt",
         "-i", input_path,
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
         "-pix_fmt", "yuv420p",
         "-movflags", "+faststart", output_path],
    ]

    for cmd in strategies:
        rc, err = _run_ffmpeg(cmd)
        if rc == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            return True, ""

    return False, err


class MatrixParser(BaseDVRParser):
    """
    Parser for Matrix Comsec SATATYA DVR/NVR evidence.
    Supports native SATATYA stream formats (.stm, .mxs, .avs) and raw disk images.
    """

    vendor_name    = "matrix"
    parser_version = "0.1.0"
    max_confidence = 0.82

    # ── detect ────────────────────────────────────────────────────────────────
    def detect(self, evidence_path: str) -> tuple[bool, float, dict]:
        try:
            p = Path(evidence_path)
            if not p.exists() or not p.is_file():
                return False, 0.0, {}
            size = p.stat().st_size
            if size < _MIN_SIZE:
                return False, 0.0, {}

            with open(p, "rb") as f:
                head = f.read(min(_BRAND_SCAN_BYTES, size))

            has_brand = _contains_matrix_brand(head)
            ext       = p.suffix.lower()

            # --- Native Matrix file extensions ---
            if ext in MATRIX_EXTS:
                if has_brand:
                    return True, 0.82, {
                        "vendor":    "matrix",
                        "format":    f"satatya_{ext[1:]}",
                        "extension": ext,
                        "brand_detected": True,
                    }
                # Extension match without brand: moderate confidence
                # .stm/.mxs are very Matrix-specific, trust them
                if ext in {".stm", ".mxs"}:
                    return True, 0.70, {
                        "vendor":    "matrix",
                        "format":    f"satatya_{ext[1:]}",
                        "extension": ext,
                        "brand_detected": False,
                    }

            # --- Raw disk image or unknown container with Matrix brand strings ---
            if has_brand:
                # Check for NAL video content
                with open(p, "rb") as f:
                    f.seek(min(_BRAND_SCAN_BYTES, size))
                    body = f.read(min(_NAL_SCAN_BYTES, size))

                nal_starts = _find_nal_starts(head + body)
                if nal_starts:
                    return True, 0.78, {
                        "vendor":       "matrix",
                        "format":       "satatya_disk_image",
                        "brand_detected": True,
                        "nal_units_found": len(nal_starts),
                    }

                # Brand only — no decodable NAL yet
                return True, 0.62, {
                    "vendor":       "matrix",
                    "format":       "satatya_brand_only",
                    "brand_detected": True,
                    "nal_units_found": 0,
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
            if p.stat().st_size < _MIN_SIZE:
                return False, ["Evidence file too small"]

            with open(p, "rb") as f:
                data = f.read(min(_BRAND_SCAN_BYTES + _NAL_SCAN_BYTES, p.stat().st_size))

            has_brand = _contains_matrix_brand(data[:_BRAND_SCAN_BYTES])
            nal       = _find_nal_starts(data)

            if not has_brand:
                warnings.append("No Matrix Comsec / SATATYA brand strings found in first 64 KB")
            if not nal:
                warnings.append(
                    "No H.264/H.265 NAL units found; SATATYA native streams may require "
                    "Matrix Device Player for initial conversion"
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
            scan_size = min(size, _BRAND_SCAN_BYTES + _NAL_SCAN_BYTES)

            with open(p, "rb") as f:
                data = f.read(scan_size)

            nal_starts = _find_nal_starts(data)
            ext        = p.suffix.lower()

            if not nal_starts:
                # For native extensions, report as parseable even without NAL
                # — FFmpeg may still demux them
                if ext in MATRIX_EXTS:
                    warnings.append(
                        f"No NAL units found in first {scan_size // 1024 // 1024} MB. "
                        "Will attempt direct FFmpeg demux during extraction."
                    )
                    recordings = [NormalizedRecording(
                        camera_id="CH-00",
                        recording_id=f"matrix-{p.stem}-0000",
                        source_path=evidence_path,
                        extracted_path=None,
                        original_timestamp=None,
                        normalized_timestamp=None,
                        duration_seconds=None,
                        resolution=None,
                        fps=None,
                        codec="h264",
                        file_size=size,
                        recovery_status="ORIGINAL",
                        device_model="Matrix Comsec SATATYA",
                        raw_metadata={
                            "format": f"satatya_{ext[1:]}",
                            "direct_ffmpeg": True,
                        },
                    )]
                    return ParseResult(
                        vendor=self.vendor_name,
                        parser_version=self.parser_version,
                        success=True,
                        recordings=recordings,
                        warnings=warnings,
                        raw_master_block={"format": f"satatya_{ext[1:]}", "nal_found": False},
                    )

                return ParseResult(
                    vendor=self.vendor_name,
                    parser_version=self.parser_version,
                    success=False,
                    error_code=ParseError.PARSE_FAILED,
                    errors=["No H.264/H.265 NAL units found in Matrix Comsec evidence file"],
                )

            # Group NAL starts into segments (gap > 1MB = new segment)
            GAP_THRESHOLD = 1024 * 1024
            segments: list[tuple[int, int]] = []
            seg_start = nal_starts[0]
            seg_end   = nal_starts[0]
            for pos in nal_starts[1:]:
                if pos - seg_end > GAP_THRESHOLD:
                    segments.append((seg_start, seg_end + 65536))
                    seg_start = pos
                seg_end = pos
            segments.append((seg_start, min(seg_end + 65536, len(data))))

            is_hevc = any(
                data[n:n+5] == H265_VPS[:5] for n in nal_starts
            )

            recordings: list[NormalizedRecording] = []
            for seg_idx, (s, e) in enumerate(segments):
                recordings.append(NormalizedRecording(
                    camera_id="CH-00",
                    recording_id=f"matrix-seg-{seg_idx:04d}",
                    source_path=evidence_path,
                    extracted_path=None,
                    original_timestamp=None,
                    normalized_timestamp=None,
                    duration_seconds=None,
                    resolution=None,
                    fps=None,
                    codec="hevc" if is_hevc else "h264",
                    file_size=e - s,
                    recovery_status="ORIGINAL",
                    device_model="Matrix Comsec SATATYA",
                    raw_metadata={
                        "segment_index": seg_idx,
                        "start_offset":  s,
                        "end_offset":    e,
                        "codec_hint":    "hevc" if is_hevc else "h264",
                        "nal_count":     sum(1 for n in nal_starts if s <= n < e),
                    },
                ))

            if len(segments) > 1:
                warnings.append(
                    f"SATATYA disk index not decoded — {len(segments)} NAL-delimited "
                    "segments identified; channel and timestamp data unavailable"
                )

            return ParseResult(
                vendor=self.vendor_name,
                parser_version=self.parser_version,
                success=True,
                recordings=recordings,
                warnings=warnings,
                raw_master_block={
                    "format":        f"satatya_{ext[1:] if ext in MATRIX_EXTS else 'disk_image'}",
                    "nal_found":     True,
                    "nal_count":     len(nal_starts),
                    "segments_found": len(segments),
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
                errors=["ffmpeg not found on PATH"],
            )

        os.makedirs(output_directory, exist_ok=True)
        warnings: list[str] = []
        errors:   list[str] = []
        updated:  list[NormalizedRecording] = []

        import dataclasses

        for rec in recordings:
            meta = rec.raw_metadata or {}

            # Direct FFmpeg extraction (native extension files)
            if meta.get("direct_ffmpeg"):
                out_path = os.path.join(output_directory, f"{rec.recording_id}.mp4")
                success, err = _try_ffmpeg_extract(evidence_path, out_path)
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
                    errors.append(f"{rec.recording_id}: direct extraction failed — {err.strip()[-200:]}")
                    updated.append(rec)
                continue

            # NAL segment carving
            seg_start = meta.get("start_offset")
            seg_end   = meta.get("end_offset")
            if seg_start is None:
                warnings.append(f"{rec.recording_id}: no segment offsets, skipped")
                updated.append(rec)
                continue

            try:
                with open(evidence_path, "rb") as f:
                    import mmap
                    with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
                        seg_data = bytes(mm[seg_start:seg_end])
            except Exception as e:
                errors.append(f"{rec.recording_id}: cannot read segment — {e}")
                updated.append(rec)
                continue

            if not seg_data:
                warnings.append(f"{rec.recording_id}: empty segment")
                updated.append(rec)
                continue

            codec_hint = meta.get("codec_hint", "h264")
            fd, tmp = tempfile.mkstemp(suffix=".bin")
            try:
                with os.fdopen(fd, "wb") as tf:
                    tf.write(seg_data)
                out_path = os.path.join(output_directory, f"{rec.recording_id}.mp4")
                success, err = _try_ffmpeg_extract(tmp, out_path)
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
                    errors.append(f"{rec.recording_id}: extraction failed — {err.strip()[-200:]}")
                    updated.append(rec)
            finally:
                if os.path.exists(tmp):
                    os.remove(tmp)

        return ParseResult(
            vendor=self.vendor_name,
            parser_version=self.parser_version,
            success=len(errors) == 0,
            recordings=updated,
            warnings=warnings,
            errors=errors,
            error_code=ParseError.PARTIALLY_PARSED if errors else None,
        )
