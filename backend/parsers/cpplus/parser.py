"""
CP Plus DVR/NVR parser.

CP Plus (also marketed as CP-Plus, manufactured by Aditya Infotech Ltd., India)
is a major Dahua Technology OEM for the Indian market. Their DVR and NVR hardware
runs Dahua-derived firmware, using the identical DHFS4.1 disk filesystem and DHAV
video frame format as Dahua devices.

Forensic differentiation from generic Dahua:
  CP Plus devices embed brand strings ("CPPLUS", "CP-PLUS", "CP PLUS",
  "aditya infotech", "Aditya Infotech") in the first 64KB of the disk image or
  in the .dav file's metadata blocks.  This parser checks for those strings
  before claiming a match, ensuring the vendor field in the forensic report
  accurately reflects "cpplus" rather than "dahua" — important for chain-of-
  custody where the specific device manufacturer must be documented.

If no CP Plus brand strings are found but DHFS4.1 or DHAV is present, the
Dahua parser (registered with higher confidence) will claim the match instead.

See backend/parsers/dahua/parser.py for full DHAV/DHFS4.1 documentation.
"""

import logging
import os
import struct
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
    _frames_to_recordings,
    _extract_dav_to_mp4,
    _probe_mp4,
)

logger = logging.getLogger(__name__)

# CP Plus brand identifiers found in disk images / metadata blocks
_CPPLUS_BRAND_STRINGS: list[bytes] = [
    b"CPPLUS",
    b"CP-PLUS",
    b"CP PLUS",
    b"aditya infotech",
    b"Aditya Infotech",
    b"ADITYA INFOTECH",
    b"cpplus",
    b"cp-plus",
    # Model prefixes common on CP Plus DVRs
    b"CP-UVR",
    b"CP-VR",
    b"CP-NVR",
]

# How much of the file to scan for brand strings
_BRAND_SCAN_BYTES = 64 * 1024   # 64 KB
_MIN_SIZE = 32


def _contains_cpplus_brand(data: bytes) -> bool:
    """Return True if any CP Plus brand string is found in `data`."""
    lower = data.lower()
    for marker in _CPPLUS_BRAND_STRINGS:
        if marker.lower() in lower:
            return True
    return False


class CPPlusParser(BaseDVRParser):
    """
    Parser for CP Plus DVR/NVR evidence.
    Shares DHFS4.1 + DHAV internals with Dahua but is registered with a lower
    max_confidence so that Dahua wins on any evidence without CP Plus branding.
    """

    vendor_name    = "cpplus"
    parser_version = "0.1.0"
    max_confidence = 0.72   # deliberately below DahuaParser (0.90)

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

            has_dhfs   = head[:7] == DHFS_SIGNATURE
            has_dhav   = head[:4] in (DHAV_MAGIC, DAHUA_MAGIC)
            has_brand  = _contains_cpplus_brand(head)

            if not (has_dhfs or has_dhav):
                # Scan first 4MB for embedded frames
                if p.stat().st_size > _BRAND_SCAN_BYTES:
                    with open(p, "rb") as f:
                        scan = f.read(4 * 1024 * 1024)
                    frames = _scan_dhav_frames(scan)
                    if len(frames) < 3:
                        return False, 0.0, {}
                    has_brand = has_brand or _contains_cpplus_brand(scan[:_BRAND_SCAN_BYTES])
                else:
                    return False, 0.0, {}

            if not has_brand:
                # No CP Plus brand strings — don't claim; let Dahua parser handle it
                return False, 0.0, {}

            confidence = 0.72
            fmt = "dhfs_disk_image" if has_dhfs else "dav_stream" if has_dhav else "dhav_embedded"
            return True, confidence, {
                "vendor": "cpplus",
                "format": fmt,
                "brand_detected": True,
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
                return False, ["Evidence file too small"]

            with open(p, "rb") as f:
                head = f.read(min(_BRAND_SCAN_BYTES, p.stat().st_size))

            if head[:7] == DHFS_SIGNATURE:
                return True, warnings
            if head[:4] in (DHAV_MAGIC, DAHUA_MAGIC):
                return True, warnings

            frames = _scan_dhav_frames(head)
            if frames:
                return True, warnings

            return False, ["No DHFS4.1 or DHAV frames found in CP Plus evidence file"]
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
                scan_size = min(size, 64 * 1024 * 1024)
                data = f.read(scan_size)

            is_disk = data[:7] == DHFS_SIGNATURE
            frames = _scan_dhav_frames(data)

            if not frames and size > len(data):
                warnings.append("No frames in first 64MB; running full-disk scan")
                import mmap
                with open(p, "rb") as f:
                    with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
                        chunk_size = 8 * 1024 * 1024
                        offset = scan_size
                        while offset < size:
                            chunk = bytes(mm[offset:offset + chunk_size])
                            frames.extend(_scan_dhav_frames(chunk))
                            offset += chunk_size
                            if len(frames) >= 1000:
                                warnings.append("Frame scan capped at 1000")
                                break

            if not frames:
                return ParseResult(
                    vendor=self.vendor_name,
                    parser_version=self.parser_version,
                    success=False,
                    error_code=ParseError.PARSE_FAILED,
                    errors=["No DHAV frames found in CP Plus evidence file"],
                )

            recordings = _frames_to_recordings(frames, evidence_path, self.vendor_name)
            # Rebrand device_model
            import dataclasses
            recordings = [
                dataclasses.replace(r, device_model="CP Plus DVR/NVR")
                for r in recordings
            ]

            return ParseResult(
                vendor=self.vendor_name,
                parser_version=self.parser_version,
                success=True,
                recordings=recordings,
                warnings=warnings,
                raw_master_block={
                    "format": "dhfs_disk_image" if is_disk else "dhav_stream",
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
        """Delegates to the same DHAV extraction pipeline as DahuaParser."""
        from backend.parsers.dahua.parser import DahuaParser
        dahua = DahuaParser()
        result = dahua.extract_recordings(
            evidence_path, output_directory, recordings, raw_master_block
        )
        # Fix vendor label so DB reports "cpplus"
        import dataclasses
        result = dataclasses.replace(
            result,
            vendor=self.vendor_name,
            recordings=[
                dataclasses.replace(r, device_model="CP Plus DVR/NVR")
                for r in result.recordings
            ],
        )
        return result
