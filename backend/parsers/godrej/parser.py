"""
Godrej Security Solutions DVR/NVR parser.

Godrej Security Solutions (GSS) — a division of Godrej & Boyce Mfg. Co. Ltd.,
Mumbai, India — is a major Indian security brand. Their DVR/NVR hardware is
sourced from two global ODMs, creating two distinct hardware lines:

────────────────────────────────────────────────────────────────────────────
LINE A — DAHUA TECHNOLOGY OEM  (Mid-range & enterprise: STE-UR, STE-NVR series)

  Models: STE-UR4S1, STE-UR8S1, STE-UR16S1 (5-in-1 UVR), STE-NVR series
  Firmware: Dahua embedded Linux DVR/NVR stack
  Network:  Default ports 37777 / 80 / 554 (identical to Dahua)
  Filesystem: DHFS4.1 at sector 0
  Frame container: DHAV ("DHAV" header, "dhav" footer)
  Export: Native .dav → convertible to MP4 via FFmpeg
  ConfigTool compatibility: Dahua ConfigTool, SmartPSS, gDMSS

  Detection note: If DHFS4.1 is detected at sector 0 AND Godrej brand strings
  are found → claim as Godrej (overrides DahuaParser). If no Godrej strings
  but DHFS4.1 is present → DahuaParser handles it.

────────────────────────────────────────────────────────────────────────────
LINE B — XIONGMAI (XM / XMEye) OEM  (Entry / Eco line)

  Models: SeeThru Eco 4/8-channel, ACE Smart, ACE Wi-Fi series
  Firmware: Xiongmai "Sofia" Linux OS (board IDs: AHB7004T, AHB7008T, etc.)
  Network:  Default port 34567 (Xiongmai proprietary), HTTP 80
  Compatibility: XMEye, vMEye, General CMS, NVTools

  Disk structure: Unallocated raw sectors partitioned into circular
  64 MB / 128 MB chunk buffers (no standard filesystem visible to host OS)

  SYNC MARKER (per-frame block sync in raw disk):
    AA 55 AA 55  (\xaa\x55\xaa\x55)  — primary Xiongmai block sync tag
    5A A5 5A A5  (\x5a\xa5\x5a\xa5)  — alternate sync tag on some firmware

  FRAME PREFIXES (preceding H.264 NAL units):
    00 00 01 FD  — I-frame marker
    00 00 01 FC  — P-frame / B-frame marker

  Export format: .264, .h264, or .avi (custom H264 FOURCC)

────────────────────────────────────────────────────────────────────────────
BRAND STRINGS (both lines, appear in disk metadata, firmware blobs, configs):
  b"GODREJ"   b"Godrej"   b"GODREJ SECURITY"   b"GSS"
  b"SeeThru"  b"STE-UR"   b"STE-NVR"           b"Godrej ACE"

Source: Research subagent findings, SIH 2026 Problem Statement SIH26150,
        Magnet DVR Examiner forensic profile documentation.
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
from backend.parsers.dahua.parser import (
    DHAV_ALL_TYPES,
    DHAV_MAGIC,
    DAHUA_MAGIC,
    DHFS_SIGNATURE,
    _scan_dhav_frames,
    _frames_to_recordings as _dhav_frames_to_recordings,
    _extract_dav_to_mp4,
    _probe_mp4,
)

logger = logging.getLogger(__name__)

# ── Godrej brand strings ──────────────────────────────────────────────────────
GODREJ_BRAND_STRINGS: list[bytes] = [
    b"GODREJ",
    b"Godrej",
    b"godrej",
    b"GODREJ SECURITY",
    b"Godrej GSS",
    b"SeeThru",
    b"seethru",
    b"STE-UR",
    b"STE-NVR",
    b"Godrej ACE",
    b"Godrej Security",
]

# ── Xiongmai markers ──────────────────────────────────────────────────────────
XM_SYNC_MARKERS: list[bytes] = [
    b"\xaa\x55\xaa\x55",   # primary Xiongmai block sync
    b"\x5a\xa5\x5a\xa5",   # alternate sync
]
XM_IFRAME_PREFIX = b"\x00\x00\x01\xfd"
XM_PFRAME_PREFIX = b"\x00\x00\x01\xfc"

_BRAND_SCAN_BYTES = 64 * 1024
_SCAN_BYTES       = 8 * 1024 * 1024
_MIN_SIZE         = 32


def _contains_godrej_brand(data: bytes) -> bool:
    lower = data.lower()
    for marker in GODREJ_BRAND_STRINGS:
        if marker.lower() in lower:
            return True
    return False


def _scan_xm_frames(data: bytes) -> list[dict]:
    """Find Xiongmai I-frame markers in a byte buffer."""
    frames: list[dict] = []
    pos = 0
    while pos < len(data) - 4:
        idx = data.find(XM_IFRAME_PREFIX, pos)
        if idx == -1:
            break
        frames.append({"offset": idx, "frame_type": "iframe"})
        pos = idx + 4
    return frames


def _run_ffmpeg(cmd: list[str]) -> tuple[int, str]:
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return p.returncode, p.stderr.decode("utf-8", "ignore")


class GodrejParser(BaseDVRParser):
    """
    Parser for Godrej Security Solutions DVR/NVR evidence.

    Detects both hardware lines:
    - Line A: Dahua OEM (DHFS4.1 + DHAV) — uses DHAV parsing pipeline
    - Line B: Xiongmai OEM (AA55AA55 sync + XM frame tags) — uses NAL carving
    """

    vendor_name    = "godrej"
    parser_version = "0.1.0"
    max_confidence = 0.80

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

            has_brand = _contains_godrej_brand(head)

            # --- Line A: Dahua OEM (DHFS4.1) ---
            if head[:7] == DHFS_SIGNATURE:
                if has_brand:
                    return True, 0.80, {
                        "vendor": "godrej",
                        "format": "godrej_dahua_oem",
                        "line":   "A_dahua_oem",
                        "signature": "DHFS4.1",
                    }
                # DHFS4.1 without Godrej brand → let DahuaParser handle it
                return False, 0.0, {}

            # --- Line A: .dav file with DHAV magic ---
            if p.suffix.lower() == ".dav" and head[:4] in (DHAV_MAGIC, DAHUA_MAGIC):
                if has_brand:
                    return True, 0.78, {
                        "vendor": "godrej",
                        "format": "godrej_dahua_oem_dav",
                        "line":   "A_dahua_oem",
                    }
                return False, 0.0, {}

            # --- Line B: Xiongmai OEM ---
            # Look for XM sync markers OR XM frame prefixes combined with brand strings
            has_xm_sync  = any(m in head for m in XM_SYNC_MARKERS)
            has_xm_frame = XM_IFRAME_PREFIX in head or XM_PFRAME_PREFIX in head

            if (has_xm_sync or has_xm_frame) and has_brand:
                return True, 0.75, {
                    "vendor": "godrej",
                    "format": "godrej_xiongmai_oem",
                    "line":   "B_xiongmai_oem",
                    "xm_sync_found":  has_xm_sync,
                    "xm_frame_found": has_xm_frame,
                }

            # Brand strings only (DHAV scan fallback)
            if has_brand:
                with open(p, "rb") as f:
                    scan_data = f.read(min(_SCAN_BYTES, size))
                dhav_frames = _scan_dhav_frames(scan_data)
                xm_frames   = _scan_xm_frames(scan_data)
                if dhav_frames:
                    return True, 0.72, {
                        "vendor": "godrej",
                        "format": "godrej_dahua_oem",
                        "line":   "A_dahua_oem",
                        "dhav_frames_found": len(dhav_frames),
                    }
                if xm_frames:
                    return True, 0.68, {
                        "vendor": "godrej",
                        "format": "godrej_xiongmai_oem",
                        "line":   "B_xiongmai_oem",
                        "xm_frames_found": len(xm_frames),
                    }
                # Brand only, no decodable frames yet
                return True, 0.60, {
                    "vendor": "godrej",
                    "format": "godrej_brand_only",
                    "brand_detected": True,
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
                data = f.read(min(_SCAN_BYTES, p.stat().st_size))

            if head := data[:7]:
                if head == DHFS_SIGNATURE:
                    return True, warnings

            dhav = _scan_dhav_frames(data[:_BRAND_SCAN_BYTES])
            xm   = _scan_xm_frames(data[:_BRAND_SCAN_BYTES])
            if not dhav and not xm:
                warnings.append(
                    "No DHAV frames or Xiongmai sync markers found; "
                    "file may require deeper scan or is a different format"
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

            with open(p, "rb") as f:
                scan_data = f.read(min(64 * 1024 * 1024, size))

            is_dahua_oem = scan_data[:7] == DHFS_SIGNATURE or scan_data[:4] in (DHAV_MAGIC, DAHUA_MAGIC)

            # --- Line A: DHAV ---
            dhav_frames = _scan_dhav_frames(scan_data)
            if dhav_frames:
                recordings = _dhav_frames_to_recordings(dhav_frames, evidence_path, self.vendor_name)
                import dataclasses
                recordings = [dataclasses.replace(r, device_model="Godrej DVR/NVR (Dahua OEM)") for r in recordings]
                return ParseResult(
                    vendor=self.vendor_name,
                    parser_version=self.parser_version,
                    success=True,
                    recordings=recordings,
                    warnings=warnings,
                    raw_master_block={
                        "format":       "godrej_dahua_oem",
                        "line":         "A_dahua_oem",
                        "frames_found": len(dhav_frames),
                    },
                )

            # --- Line B: Xiongmai ---
            xm_frames = _scan_xm_frames(scan_data)
            if xm_frames:
                # Build one recording per contiguous XM stream
                recordings = [NormalizedRecording(
                    camera_id="CH-00",
                    recording_id=f"{self.vendor_name}-xm-{i:04d}",
                    source_path=evidence_path,
                    extracted_path=None,
                    original_timestamp=None,
                    normalized_timestamp=None,
                    duration_seconds=None,
                    resolution=None,
                    fps=None,
                    codec="h264",
                    file_size=None,
                    recovery_status="ORIGINAL",
                    device_model="Godrej DVR/NVR (Xiongmai OEM)",
                    raw_metadata={
                        "segment_index": i,
                        "offset": fr["offset"],
                        "line":   "B_xiongmai_oem",
                    },
                ) for i, fr in enumerate(xm_frames[:50])]

                warnings.append(
                    "Xiongmai OEM hardware detected. Timestamps and channel IDs "
                    "are unavailable without the XM block index table."
                )
                return ParseResult(
                    vendor=self.vendor_name,
                    parser_version=self.parser_version,
                    success=True,
                    recordings=recordings,
                    warnings=warnings,
                    raw_master_block={
                        "format": "godrej_xiongmai_oem",
                        "line":   "B_xiongmai_oem",
                        "xm_iframes_found": len(xm_frames),
                    },
                )

            return ParseResult(
                vendor=self.vendor_name,
                parser_version=self.parser_version,
                success=False,
                error_code=ParseError.PARSE_FAILED,
                errors=["No DHAV frames or Xiongmai stream markers found in Godrej evidence file"],
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

        rmb = raw_master_block if isinstance(raw_master_block, dict) else {}
        line = rmb.get("line", "A_dahua_oem")

        if "dahua" in line:
            from backend.parsers.dahua.parser import DahuaParser
            import dataclasses
            dahua = DahuaParser()
            result = dahua.extract_recordings(evidence_path, output_directory, recordings, raw_master_block)
            result = dataclasses.replace(
                result,
                vendor=self.vendor_name,
                recordings=[dataclasses.replace(r, device_model="Godrej DVR/NVR (Dahua OEM)") for r in result.recordings],
            )
            return result

        # Xiongmai: carve raw H.264 stream around XM I-frame markers
        os.makedirs(output_directory, exist_ok=True)
        warnings: list[str] = []
        errors:   list[str] = []
        updated:  list[NormalizedRecording] = []

        try:
            with open(evidence_path, "rb") as f:
                import mmap
                with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
                    data = bytes(mm[:min(len(mm), 64 * 1024 * 1024)])
        except Exception as e:
            return ParseResult(
                vendor=self.vendor_name, parser_version=self.parser_version,
                success=False, error_code=ParseError.EXTRACTION_FAILED,
                errors=[f"Cannot read evidence: {e}"],
            )

        import dataclasses

        for rec in recordings:
            meta   = rec.raw_metadata or {}
            offset = meta.get("offset")
            if offset is None:
                updated.append(rec)
                continue

            # Carve from this I-frame to the next or end of data
            next_iframe = data.find(XM_IFRAME_PREFIX, offset + 4)
            end = next_iframe if next_iframe > offset else min(offset + 10 * 1024 * 1024, len(data))
            segment = data[offset:end]
            if len(segment) < 100:
                warnings.append(f"{rec.recording_id}: carved segment too small")
                updated.append(rec)
                continue

            fd, tmp = tempfile.mkstemp(suffix=".h264")
            try:
                with os.fdopen(fd, "wb") as tf:
                    tf.write(segment)
                out_path = os.path.join(output_directory, f"{rec.recording_id}.mp4")
                rc, err = _run_ffmpeg([
                    "ffmpeg", "-y", "-f", "h264",
                    "-fflags", "+genpts+discardcorrupt",
                    "-i", tmp,
                    "-c:v", "copy", "-movflags", "+faststart",
                    out_path,
                ])
                if os.path.exists(out_path) and os.path.getsize(out_path) > 0:
                    probe = _probe_mp4(out_path)
                    updated.append(dataclasses.replace(
                        rec,
                        extracted_path=out_path,
                        recovery_status="RECOVERED",
                        duration_seconds=probe.get("duration_seconds"),
                        resolution=probe.get("resolution"),
                        fps=probe.get("fps"),
                        codec=probe.get("codec", "h264"),
                        device_model="Godrej DVR/NVR (Xiongmai OEM)",
                    ))
                else:
                    errors.append(f"{rec.recording_id}: extraction failed")
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
