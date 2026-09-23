"""
Honeywell Security DVR/NVR parser.

Honeywell Security operates across THREE distinct hardware architectures:

────────────────────────────────────────────────────────────────────────
A. HONEYWELL PROPRIETARY SURVEILLANCE FILESYSTEM (Modern Standalone NVRs)
   Documented by Yoon & Hwang (DFRWS USA 2026, arXiv:2605.07430):
   "Forensic analysis of video data deletion and recovery in Honeywell
   surveillance file system"

   DISK LAYOUT:
     Sector 0–33:  MBR / GPT metadata
     Sector 34:    Machine Data Region (0x4400–0x45FF)
                   → Brand strings: "Honeywell", model, serial
     Partition 1:  Proprietary Video Storage
       0x0000–0x3FFF: Partition header (starting offset, write ptr, free space)
       0x40000–0x3FFFFF: Video Block List (16-byte entries)
       0x400000–0x3FFFFFFF: Video Channel List
       Remainder: Video Data Region (H.264/H.265 NAL preceded by 20-byte headers)
     Partition 2:  10 GB ext4 Linux system partition

   VIDEO BLOCK LIST ENTRY (16 bytes, Little-Endian):
     uint32_t  start_timestamp   Unix epoch timestamp
     uint32_t  block_number      Physical block index
     uint32_t  block_group       Block group identifier
     uint32_t  flags             Status / recording-type flags

   20-BYTE NAL HEADER (prepended to every H.264/H.265 NAL unit):
     uint8_t   frame_type        0x82=IDR (I-Frame), 0x02=non-IDR (P/B-Frame)
     uint8_t[3] magic            Fixed: 0x80 0x01 0x00
     uint16_t  width             Video width (LE, e.g. 1920=0x0780)
     uint16_t  height            Video height (LE, e.g. 1080=0x0438)
     uint32_t  nal_length        Byte length of following NAL unit (LE)
     uint64_t  timestamp_us      Unix microsecond timestamp (LE)

   END-OF-CHANNEL MARKER: 20 consecutive 0x00 bytes

────────────────────────────────────────────────────────────────────────
B. PERFORMANCE SERIES — DAHUA OEM  (HEN, HRHD, HRHQ, HRHT series)
   Superblock: "DHFS4.1" at sector 0 → detect via DahuaParser, not here.

C. PERFORMANCE SERIES — HIKVISION OEM  (HRGX series, legacy)
   Superblock: "HIKVISION@HANGZHOU" at sector 0/544 → detect via HikvisionParser.

D. MAXPRO PLATFORM (NVR XE/SE/PE/HE)
   Windows NTFS + SQL Server. Exports: .mpvc, .smpvc, .wmv, .asf
   .mpvc files detected by Honeywell brand strings in first 64 KB.

Detection priority:
  1. Scan Sector 34 (offset 0x4400) for Honeywell brand strings → proprietary FS
  2. Scan first 64 KB for 20-byte NAL header magic (82 80 01 00 or 02 80 01 00)
  3. Check for .mpvc / .smpvc extension with Honeywell strings → MAXPRO export
  4. If DHFS4.1 at sector 0 → return False (DahuaParser handles it)
  5. If HIKVISION at sector 0 → return False (HikvisionParser handles it)

Source: Yoon & Hwang (2026), arXiv:2605.07430; GitHub eraw1am/Honeywell-NVR-Filesystem-Tools
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

from backend.parsers.common.base import (
    BaseDVRParser,
    NormalizedRecording,
    ParseError,
    ParseResult,
)

logger = logging.getLogger(__name__)

# ── Magic bytes ───────────────────────────────────────────────────────────────
# Honeywell proprietary NAL frame header magic (bytes 1-3 following frame_type)
HON_NAL_MAGIC       = b"\x80\x01\x00"
HON_IDR_FRAME_TYPE  = 0x82   # I-frame
HON_NONDIR_TYPE     = 0x02   # P/B-frame
HON_VALID_TYPES     = {HON_IDR_FRAME_TYPE, HON_NONDIR_TYPE}

# End-of-channel marker
HON_EOC_MARKER      = b"\x00" * 20

# Disk offsets
SECTOR_SIZE         = 512
MACHINE_DATA_SECTOR = 34
MACHINE_DATA_OFFSET = SECTOR_SIZE * MACHINE_DATA_SECTOR   # 0x4400

# Conflicting superblocks we must NOT claim
DHFS_SIGNATURE      = b"DHFS4.1"
HIK_SIGNATURE       = b"HIKVISION@HANGZHOU"

# Honeywell brand identifiers (appear in Sector 34 machine data and config)
HONEYWELL_BRAND_STRINGS: list[bytes] = [
    b"Honeywell",
    b"HONEYWELL",
    b"MAXPRO",
    b"honeywell",
    b"HEN",        # HEN-series NVRs
    b"HRHD",       # Performance DVR
    b"HRHQ",       # Performance DVR
    b"HRHT",       # Performance DVR
    b"HRGX",       # Hikvision-OEM legacy (still report as Honeywell)
    b"Ademco",     # Legacy Honeywell / Ademco brand
]

# MAXPRO export extensions
MAXPRO_EXTS = {".mpvc", ".smpvc"}

_BRAND_SCAN_BYTES = 64 * 1024   # 64 KB
_MIN_SIZE         = 64
_NAL_SCAN_BYTES   = 8 * 1024 * 1024   # 8 MB


# ── 20-byte NAL header struct ─────────────────────────────────────────────────
# < = little-endian, B=uint8, H=uint16, I=uint32, Q=uint64
_HON_NAL_HDR_FMT    = "<4sHHIQ"   # frame_type+magic[3], width, height, nal_len, ts_us
_HON_NAL_HDR_SIZE   = struct.calcsize(_HON_NAL_HDR_FMT)   # 20 bytes


def _decode_hon_nal_header(data: bytes, offset: int) -> dict | None:
    """Parse a 20-byte Honeywell NAL header starting at `offset`. Returns None if invalid."""
    if offset + 20 > len(data):
        return None
    try:
        first4, width, height, nal_len, ts_us = struct.unpack_from(_HON_NAL_HDR_FMT, data, offset)
    except struct.error:
        return None

    frame_type = first4[0]
    magic3     = first4[1:4]

    if frame_type not in HON_VALID_TYPES:
        return None
    if magic3 != HON_NAL_MAGIC:
        return None
    if nal_len == 0 or nal_len > 100 * 1024 * 1024:   # sanity: NAL < 100 MB
        return None

    ts = None
    if ts_us > 0:
        try:
            ts = datetime.fromtimestamp(ts_us / 1_000_000, tz=timezone.utc)
            # Sanity: must be between 2000 and 2100
            if not (2000 <= ts.year <= 2099):
                ts = None
        except (OSError, OverflowError, ValueError):
            ts = None

    return {
        "frame_type": frame_type,
        "width":      width,
        "height":     height,
        "nal_len":    nal_len,
        "timestamp":  ts,
        "ts_us":      ts_us,
    }


def _scan_hon_nal_frames(data: bytes) -> list[dict]:
    """
    Scan a byte buffer for Honeywell 20-byte NAL headers.
    Each valid header immediately followed by nal_len bytes of H.264/H.265 NAL data.
    """
    frames: list[dict] = []
    pos = 0
    data_len = len(data)

    while pos < data_len - 20:
        # Search for the fixed magic 3-byte sequence at bytes [1:4] of header
        idx = data.find(HON_NAL_MAGIC, pos + 1)
        if idx == -1:
            break

        # The frame_type is at idx - 1
        header_start = idx - 1
        if header_start < 0:
            pos = idx + 1
            continue

        hdr = _decode_hon_nal_header(data, header_start)
        if hdr is None:
            pos = idx + 1
            continue

        frames.append({
            "offset":     header_start,
            "frame_type": hdr["frame_type"],
            "width":      hdr["width"],
            "height":     hdr["height"],
            "nal_len":    hdr["nal_len"],
            "timestamp":  hdr["timestamp"],
        })

        # Jump past this NAL (header + payload)
        pos = header_start + 20 + hdr["nal_len"]

    return frames


def _contains_honeywell_brand(data: bytes) -> bool:
    lower = data.lower()
    for marker in HONEYWELL_BRAND_STRINGS:
        if marker.lower() in lower:
            return True
    return False


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


def _frames_to_recordings(
    frames: list[dict], evidence_path: str, vendor: str
) -> list[NormalizedRecording]:
    if not frames:
        return []

    # Group into segments by IDR (I-frame) boundaries
    segments: list[list[dict]] = []
    current: list[dict] = []
    for f in frames:
        if f["frame_type"] == HON_IDR_FRAME_TYPE and current:
            segments.append(current)
            current = []
        current.append(f)
    if current:
        segments.append(current)

    recordings: list[NormalizedRecording] = []
    for seg_idx, seg in enumerate(segments):
        valid_ts = [f["timestamp"] for f in seg if f["timestamp"] is not None]
        start_ts = min(valid_ts) if valid_ts else None
        first    = seg[0]
        res      = f"{first['width']}x{first['height']}" if first["width"] and first["height"] else None
        total_b  = sum(20 + f["nal_len"] for f in seg)

        recordings.append(NormalizedRecording(
            camera_id=f"CH-00",
            recording_id=f"{vendor}-seg-{seg_idx:04d}",
            source_path=evidence_path,
            extracted_path=None,
            original_timestamp=start_ts,
            normalized_timestamp=start_ts,
            duration_seconds=None,
            resolution=res,
            fps=None,
            codec="h264",
            file_size=total_b,
            recovery_status="ORIGINAL",
            device_model="Honeywell DVR/NVR",
            raw_metadata={
                "segment_index": seg_idx,
                "frame_count":   len(seg),
                "first_offset":  seg[0]["offset"],
                "last_offset":   seg[-1]["offset"],
                "width":         first["width"],
                "height":        first["height"],
            },
        ))

    return recordings


# ── Parser class ──────────────────────────────────────────────────────────────
class HoneywellParser(BaseDVRParser):
    """
    Parser for Honeywell Security DVR/NVR evidence:
    - Honeywell proprietary surveillance filesystem (standalone NVRs)
    - MAXPRO platform exports (.mpvc, .smpvc)
    - Performance Series Dahua/Hikvision OEM → delegated to respective parsers
    """

    vendor_name    = "honeywell"
    parser_version = "0.1.0"
    max_confidence = 0.85

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

            # --- Do NOT claim Dahua or Hikvision superblocks ---
            if head[:7] == DHFS_SIGNATURE:
                return False, 0.0, {}
            if head[:18] == HIK_SIGNATURE:
                return False, 0.0, {}

            # --- Check MAXPRO export extensions ---
            if p.suffix.lower() in MAXPRO_EXTS:
                if _contains_honeywell_brand(head):
                    return True, 0.80, {
                        "vendor": "honeywell",
                        "format": "maxpro_export",
                        "extension": p.suffix.lower(),
                    }

            # --- Check Sector 34 (offset 0x4400) for Honeywell machine data ---
            has_brand_head = _contains_honeywell_brand(head)

            if size > MACHINE_DATA_OFFSET:
                with open(p, "rb") as f:
                    f.seek(MACHINE_DATA_OFFSET)
                    sector34 = f.read(512)
                has_brand_s34 = _contains_honeywell_brand(sector34)
            else:
                has_brand_s34 = False

            # --- Scan for 20-byte Honeywell NAL headers ---
            scan_bytes = min(_NAL_SCAN_BYTES, size)
            with open(p, "rb") as f:
                body = f.read(scan_bytes)

            frames = _scan_hon_nal_frames(body)

            if has_brand_s34 and frames:
                return True, 0.85, {
                    "vendor": "honeywell",
                    "format": "honeywell_proprietary_fs",
                    "brand_in_sector34": True,
                    "nal_frames_found": len(frames),
                }

            if (has_brand_head or has_brand_s34) and len(frames) >= 2:
                return True, 0.82, {
                    "vendor": "honeywell",
                    "format": "honeywell_proprietary_fs",
                    "brand_detected": True,
                    "nal_frames_found": len(frames),
                }

            # Brand strings present but no proprietary NAL frames — maybe MAXPRO disk
            if has_brand_head or has_brand_s34:
                return True, 0.65, {
                    "vendor": "honeywell",
                    "format": "honeywell_brand_detected",
                    "brand_detected": True,
                    "nal_frames_found": 0,
                }

            # Proprietary NAL headers found without brand strings (conservative)
            if len(frames) >= 5:
                return True, 0.70, {
                    "vendor": "honeywell",
                    "format": "honeywell_nal_pattern",
                    "brand_detected": False,
                    "nal_frames_found": len(frames),
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
                data = f.read(min(_NAL_SCAN_BYTES, p.stat().st_size))

            frames = _scan_hon_nal_frames(data)
            if not frames:
                warnings.append(
                    "No Honeywell proprietary NAL headers found; "
                    "file may be MAXPRO format or require deeper scan"
                )

            has_brand = _contains_honeywell_brand(data[:_BRAND_SCAN_BYTES])
            if not has_brand:
                warnings.append("No Honeywell brand strings found in first 64 KB")

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
            scan_size = min(size, 128 * 1024 * 1024)

            with open(p, "rb") as f:
                data = f.read(scan_size)

            frames = _scan_hon_nal_frames(data)

            if not frames and size > scan_size:
                warnings.append("No NAL frames in first 128 MB; running extended scan")
                with open(p, "rb") as f:
                    with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
                        chunk_size = 16 * 1024 * 1024
                        offset = scan_size
                        while offset < size and len(frames) < 500:
                            chunk = bytes(mm[offset:offset + chunk_size])
                            frames.extend(_scan_hon_nal_frames(chunk))
                            offset += chunk_size

            if not frames:
                return ParseResult(
                    vendor=self.vendor_name,
                    parser_version=self.parser_version,
                    success=False,
                    error_code=ParseError.PARSE_FAILED,
                    errors=["No Honeywell proprietary NAL frames found in evidence file"],
                )

            recordings = _frames_to_recordings(frames, evidence_path, self.vendor_name)

            return ParseResult(
                vendor=self.vendor_name,
                parser_version=self.parser_version,
                success=True,
                recordings=recordings,
                warnings=warnings,
                raw_master_block={
                    "format":       "honeywell_proprietary_fs",
                    "frames_found": len(frames),
                    "segments":     len(recordings),
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

        try:
            with open(evidence_path, "rb") as f:
                with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
                    data = bytes(mm[:min(len(mm), 128 * 1024 * 1024)])
        except Exception as e:
            return ParseResult(
                vendor=self.vendor_name, parser_version=self.parser_version,
                success=False, error_code=ParseError.EXTRACTION_FAILED,
                errors=[f"Could not read evidence for extraction: {e}"],
            )

        all_frames = _scan_hon_nal_frames(data)
        # Group frames back into the same segments as parse()
        segments: list[list[dict]] = []
        current: list[dict] = []
        for fr in all_frames:
            if fr["frame_type"] == HON_IDR_FRAME_TYPE and current:
                segments.append(current)
                current = []
            current.append(fr)
        if current:
            segments.append(current)

        import dataclasses

        for rec in recordings:
            meta = rec.raw_metadata or {}
            seg_idx = meta.get("segment_index")
            if seg_idx is None or seg_idx >= len(segments):
                warnings.append(f"{rec.recording_id}: segment index out of range")
                updated.append(rec)
                continue

            seg_frames = segments[seg_idx]
            # Carve raw NAL bytes: for each frame, skip the 20-byte Honeywell header
            # and write the raw H.264 Annex B NAL unit (prepending standard start code)
            raw_nal = bytearray()
            for fr in seg_frames:
                nal_start = fr["offset"] + 20
                nal_end   = nal_start + fr["nal_len"]
                if nal_end <= len(data):
                    # Prepend 4-byte Annex B start code
                    raw_nal.extend(b"\x00\x00\x00\x01")
                    raw_nal.extend(data[nal_start:nal_end])

            if not raw_nal:
                warnings.append(f"{rec.recording_id}: no NAL data carved")
                updated.append(rec)
                continue

            fd, tmp_h264 = tempfile.mkstemp(suffix=".h264")
            try:
                with os.fdopen(fd, "wb") as tf:
                    tf.write(raw_nal)

                out_path = os.path.join(output_directory, f"{rec.recording_id}.mp4")
                # Remux raw H.264 Annex B to MP4
                rc, err = _run_ffmpeg([
                    "ffmpeg", "-y",
                    "-f", "h264",
                    "-analyzeduration", "50M", "-probesize", "50M",
                    "-fflags", "+genpts+discardcorrupt",
                    "-i", tmp_h264,
                    "-c:v", "copy",
                    "-movflags", "+faststart",
                    out_path,
                ])
                if rc != 0 or not os.path.exists(out_path) or os.path.getsize(out_path) == 0:
                    # Fallback: re-encode
                    rc, err = _run_ffmpeg([
                        "ffmpeg", "-y",
                        "-f", "h264",
                        "-fflags", "+genpts+discardcorrupt",
                        "-i", tmp_h264,
                        "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
                        "-pix_fmt", "yuv420p",
                        "-movflags", "+faststart",
                        out_path,
                    ])

                if os.path.exists(out_path) and os.path.getsize(out_path) > 0:
                    probe = _probe_mp4(out_path)
                    updated.append(dataclasses.replace(
                        rec,
                        extracted_path=out_path,
                        recovery_status="RECOVERED",
                        duration_seconds=probe.get("duration_seconds"),
                        resolution=probe.get("resolution", rec.resolution),
                        fps=probe.get("fps"),
                        codec=probe.get("codec", rec.codec),
                    ))
                else:
                    errors.append(f"{rec.recording_id}: extraction failed — {err.strip()[-200:]}")
                    updated.append(rec)
            finally:
                if os.path.exists(tmp_h264):
                    os.remove(tmp_h264)

        return ParseResult(
            vendor=self.vendor_name,
            parser_version=self.parser_version,
            success=len(errors) == 0,
            recordings=updated,
            warnings=warnings,
            errors=errors,
            error_code=ParseError.PARTIALLY_PARSED if errors else None,
        )
