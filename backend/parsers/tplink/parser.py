"""
TP-Link Vigi NVR parser.

TP-Link's Vigi line of NVRs (e.g. VIGI NVR1004H, VIGI NVR2016H) records video
to attached hard drives using the DHAV container format — the same frame-level
format as Dahua DVRs — wrapped in .dav files.

Unlike Dahua's DHFS4.1 disk filesystem, TP-Link Vigi NVRs store recordings in
a Linux-compatible partition (ext4 or similar), with DHAV-encoded .dav files
organised by date/channel directories.  When the raw HDD is imaged forensically,
the disk image can be mounted or the .dav files carved from the ext4 partition.

Detection strategy:
  1. Scan first 64KB for TP-Link / Vigi brand strings.
  2. If a .dav file: check for DHAV/DAHUA magic at byte 0.
  3. For a raw disk image without DHFS4.1 but with TP-Link strings: scan for
     embedded DHAV frames.

The parser deliberately does NOT claim images that have DHFS4.1 (those belong to
Dahua) or no brand strings at all.

Extraction: identical DHAV → FFmpeg pipeline as DahuaParser.
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

_TPLINK_BRAND_STRINGS: list[bytes] = [
    b"TP-LINK",
    b"TP-Link",
    b"TPLINK",
    b"tplink",
    b"VIGI",
    b"Vigi",
    b"vigi",
    # Common TP-Link NVR model prefixes
    b"NVR1004",
    b"NVR2016",
    b"NVR4032",
]

_BRAND_SCAN_BYTES = 64 * 1024
_MIN_SIZE = 32


def _contains_tplink_brand(data: bytes) -> bool:
    for marker in _TPLINK_BRAND_STRINGS:
        if marker in data:
            return True
    return False


class TPLinkVigiParser(BaseDVRParser):
    """
    Parser for TP-Link Vigi NVR evidence (.dav files or disk images
    containing DHAV-encoded video with TP-Link branding).
    """

    vendor_name    = "tplink_vigi"
    parser_version = "0.1.0"
    max_confidence = 0.80

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

            # Never claim DHFS4.1 images — those are Dahua
            if head[:7] == DHFS_SIGNATURE:
                return False, 0.0, {}

            has_brand = _contains_tplink_brand(head)
            has_dhav  = head[:4] in (DHAV_MAGIC, DAHUA_MAGIC)

            # .dav file with DHAV magic and TP-Link branding
            if p.suffix.lower() == ".dav" and has_dhav:
                confidence = 0.80 if has_brand else 0.65
                return True, confidence, {
                    "vendor": "tplink_vigi",
                    "format": "dav_stream",
                    "brand_detected": has_brand,
                    "signature": head[:5].hex(),
                }

            # Disk image / other container with TP-Link brand strings
            if has_brand:
                frames = _scan_dhav_frames(head)
                if len(frames) >= 3:
                    return True, 0.78, {
                        "vendor": "tplink_vigi",
                        "format": "dhav_embedded",
                        "brand_detected": True,
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
            if p.stat().st_size < _MIN_SIZE:
                return False, ["Evidence file too small"]

            with open(p, "rb") as f:
                head = f.read(min(_BRAND_SCAN_BYTES, p.stat().st_size))

            if head[:4] in (DHAV_MAGIC, DAHUA_MAGIC):
                if head[4] not in DHAV_ALL_TYPES:
                    warnings.append("Unexpected frame type byte; stream may be damaged")
                return True, warnings

            if _scan_dhav_frames(head):
                return True, warnings

            return False, ["No DHAV frames found in TP-Link Vigi evidence file"]
        except Exception as e:
            return False, [f"Validation failed: {e}"]

    # ── parse ─────────────────────────────────────────────────────────────────
    def parse(self, evidence_path: str, output_directory: str) -> ParseResult:
        os.makedirs(output_directory, exist_ok=True)
        warnings: list[str] = []

        try:
            p = Path(evidence_path)
            size = p.stat().st_size
            scan_size = min(size, 64 * 1024 * 1024)

            with open(p, "rb") as f:
                data = f.read(scan_size)

            frames = _scan_dhav_frames(data)

            if not frames:
                return ParseResult(
                    vendor=self.vendor_name,
                    parser_version=self.parser_version,
                    success=False,
                    error_code=ParseError.PARSE_FAILED,
                    errors=["No DHAV frames found in TP-Link Vigi evidence file"],
                )

            recordings = _frames_to_recordings(frames, evidence_path, self.vendor_name)
            import dataclasses
            recordings = [
                dataclasses.replace(r, device_model="TP-Link Vigi NVR")
                for r in recordings
            ]

            return ParseResult(
                vendor=self.vendor_name,
                parser_version=self.parser_version,
                success=True,
                recordings=recordings,
                warnings=warnings,
                raw_master_block={
                    "format": "dhav_stream",
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
        from backend.parsers.dahua.parser import DahuaParser
        dahua = DahuaParser()
        result = dahua.extract_recordings(
            evidence_path, output_directory, recordings, raw_master_block
        )
        import dataclasses
        result = dataclasses.replace(
            result,
            vendor=self.vendor_name,
            recordings=[
                dataclasses.replace(r, device_model="TP-Link Vigi NVR")
                for r in result.recordings
            ],
        )
        return result
