"""
Hikvision raw-disk-image parser.

Adapted from fmpfeifer/hikextractor (https://github.com/fmpfeifer/hikextractor).
Master block / HIKBTREE struct offsets and parsing logic are derived from that
project. Only tested/validated against filesystem version HIK.2011.03.08
(as in the original project) plus one DS-7208HQHI-SH/A sample by the original
author. Any other version is unverified — treated as a warning, not a hard fail.

License: verify and record original repo's license terms here before distribution.
"""

import mmap
import os
import struct
import subprocess
import tempfile
import dataclasses
from datetime import datetime, timezone
from typing import Optional

from backend.parsers.common.base import (
    BaseDVRParser, ParseResult, ParseError, NormalizedRecording,
)

SIGNATURE = b"HIKVISION@HANGZHOU"
HIKBTREE_SIGNATURE = b"HIKBTREE"
KNOWN_GOOD_VERSION = b"HIK.2011.03.08"
BA_NAL = bytes.fromhex("00000001BA")


@dataclasses.dataclass(frozen=True)
class MasterBlock:
    signature: bytes
    version: bytes
    capacity: int
    size_data_block: int
    total_data_blocks: int
    offset_hibtree1: int
    time_system_init: datetime


@dataclasses.dataclass(frozen=True)
class HIKBTREEEntry:
    channel: int
    recording: bool
    start_timestamp: Optional[datetime]
    end_timestamp: Optional[datetime]
    offset_datablock: int


def _u32(b, o): return struct.unpack("<I", b[o:o+4])[0]
def _u64(b, o): return struct.unpack("<Q", b[o:o+8])[0]
def _u8(b, o): return struct.unpack("B", b[o:o+1])[0]
def _dt(b, o): return datetime.fromtimestamp(_u32(b, o), tz=timezone.utc)


def _parse_master_block(mm) -> MasterBlock:
    m = mm[0x200:0x360]
    sig = bytes(m[0x10:0x22])
    if sig != SIGNATURE:
        raise ValueError("master block signature mismatch")
    return MasterBlock(
        signature=sig,
        version=bytes(m[0x30:0x3E]),
        capacity=_u64(m, 0x48),
        size_data_block=_u64(m, 0x88),
        total_data_blocks=_u32(m, 0x90),
        offset_hibtree1=_u64(m, 0x98),
        time_system_init=_dt(m, 0xF0),
    )


def _parse_hbt_entry(data, offset) -> Optional[HIKBTREEEntry]:
    has_footage = _u64(data, offset + 0x8) == 0
    if not has_footage:
        return None
    channel = _u8(data, offset + 0x11)
    dt1 = _u32(data, offset + 0x18)
    offset_datablock = _u64(data, offset + 0x20)
    if dt1 == 0x7FFFFFFF:
        return HIKBTREEEntry(channel, True, None, None, offset_datablock)
    return HIKBTREEEntry(channel, False, _dt(data, offset + 0x18), _dt(data, offset + 0x1C), offset_datablock)


def _parse_hbtree(mm, master: MasterBlock) -> list[HIKBTREEEntry]:
    offset = master.offset_hibtree1
    if bytes(mm[offset + 0x10: offset + 0x18]) != HIKBTREE_SIGNATURE:
        raise ValueError("HIKBTREE signature mismatch")
    offset_page = _u64(mm, offset + 0x58)
    entries, safe_count = [], 0
    while True:
        entry_count = _u32(mm, offset_page + 0x10)
        next_page = _u64(mm, offset_page + 0x20)
        first_entry = offset_page + 0x60
        for i in range(entry_count):
            e = _parse_hbt_entry(mm, first_entry + i * 48)
            if e:
                entries.append(e)
        if next_page == 0xFFFFFFFFFFFFFFFF or safe_count > 100:
            break
        offset_page = next_page
        safe_count += 1
    return entries


def _find_first_ps_pack(data: bytes) -> int:
    """MPEG-PS pack start code, searched in first ~2MiB only."""
    return data[:2 * 1024 * 1024].find(BA_NAL)


def _run_ffmpeg(cmd: list[str]) -> tuple[int, str]:
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return p.returncode, p.stderr.decode("utf-8", "ignore")


class HikvisionParser(BaseDVRParser):
    vendor_name = "hikvision"
    parser_version = "0.1.0"

    def detect(self, evidence_path: str) -> tuple[bool, float, dict]:
        try:
            with open(evidence_path, "rb") as f, \
                 mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
                if len(mm) < 0x360:
                    return False, 0.0, {}
                sig = bytes(mm[0x210:0x222])
                if sig == SIGNATURE:
                    version = bytes(mm[0x230:0x23E])
                    return True, 0.9, {"vendor": "hikvision", "version": version.decode(errors="replace")}
                return False, 0.0, {}
        except (OSError, struct.error):
            return False, 0.0, {}

    def validate(self, evidence_path: str) -> tuple[bool, list[str]]:
        warnings = []
        try:
            with open(evidence_path, "rb") as f, \
                 mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
                master = _parse_master_block(mm)
                if master.version != KNOWN_GOOD_VERSION:
                    warnings.append(
                        f"Filesystem version {master.version!r} is untested by this parser "
                        f"(only {KNOWN_GOOD_VERSION!r} is confirmed). Proceeding, results may be incomplete."
                    )
                return True, warnings
        except Exception as e:
            return False, [f"Validation failed: {e}"]

    def parse(self, evidence_path: str, output_directory: str) -> ParseResult:
        warnings, recordings = [], []
        os.makedirs(output_directory, exist_ok=True)

        try:
            with open(evidence_path, "rb") as f, \
                 mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
                master = _parse_master_block(mm)
                if master.version != KNOWN_GOOD_VERSION:
                    warnings.append(f"Untested filesystem version {master.version!r}")

                entries = _parse_hbtree(mm, master)
                if not entries:
                    return ParseResult(
                        vendor=self.vendor_name, parser_version=self.parser_version,
                        success=False, error_code=ParseError.PARTIALLY_PARSED,
                        errors=["No HIKBTREE entries found — index may be corrupted or unsupported layout"],
                    )

                for i, entry in enumerate(entries):
                    if entry.recording:
                        warnings.append(f"Channel {entry.channel} block {i}: in-progress recording, no end timestamp")
                        recovery_status = "PARTIAL"
                    else:
                        recovery_status = "RECOVERED"

                    recordings.append(NormalizedRecording(
                        camera_id=f"CH-{entry.channel:02d}",
                        recording_id=f"hik-{i:06d}",
                        source_path=evidence_path,
                        extracted_path=None,
                        original_timestamp=entry.start_timestamp,
                        normalized_timestamp=entry.start_timestamp,
                        duration_seconds=None,
                        resolution=None, fps=None, codec=None,
                        file_size=master.size_data_block,
                        recovery_status=recovery_status,
                        device_model=None,
                        raw_metadata={"channel": entry.channel, "offset": entry.offset_datablock},
                    ))

            return ParseResult(
                vendor=self.vendor_name, parser_version=self.parser_version,
                success=True, recordings=recordings, warnings=warnings,
                raw_master_block=master,
            )
        except Exception as e:
            return ParseResult(
                vendor=self.vendor_name, parser_version=self.parser_version,
                success=False, error_code=ParseError.PARSE_FAILED, errors=[str(e)],
            )

    def extract_recordings(
        self, evidence_path: str, output_directory: str,
        recordings: list[NormalizedRecording], master: MasterBlock,
    ) -> ParseResult:
        import shutil as _shutil
        if _shutil.which("ffmpeg") is None:
            return ParseResult(
                vendor=self.vendor_name, parser_version=self.parser_version,
                success=False, error_code=ParseError.EXTRACTION_FAILED,
                errors=["ffmpeg not found on PATH — required for muxing recordings"],
            )

        os.makedirs(output_directory, exist_ok=True)
        warnings, errors = [], []
        updated: list[NormalizedRecording] = []
        data_block_size = master.size_data_block

        with open(evidence_path, "rb") as f, \
             mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:

            for rec in recordings:
                if rec.recovery_status == "PARTIAL":
                    updated.append(rec)
                    continue

                offset = rec.raw_metadata.get("offset")
                if offset is None:
                    warnings.append(f"{rec.recording_id}: missing block offset, skipped extraction")
                    updated.append(dataclasses.replace(rec, recovery_status="PARTIAL"))
                    continue

                block = bytes(mm[offset: offset + data_block_size])
                if not block or block.count(0) == len(block):
                    warnings.append(f"{rec.recording_id}: data block empty/zeroed, skipped")
                    updated.append(dataclasses.replace(rec, recovery_status="PARTIAL"))
                    continue

                ps_off = _find_first_ps_pack(block)
                if ps_off < 0:
                    errors.append(f"{rec.recording_id}: no MPEG-PS start code found, cannot mux")
                    updated.append(dataclasses.replace(rec, recovery_status="PARTIAL"))
                    continue

                cut = block[ps_off:]
                out_filename = f"{rec.recording_id}_CH{rec.camera_id}.mp4"
                out_path = os.path.join(output_directory, out_filename)
                if os.path.exists(out_path):
                    out_path = os.path.join(
                        output_directory, f"{rec.recording_id}_CH{rec.camera_id}_dup.mp4"
                    )

                fd, tmp_in = tempfile.mkstemp(suffix=".bin")
                try:
                    with os.fdopen(fd, "wb") as tf:
                        tf.write(cut)

                    ts_path = tmp_in + ".ts"
                    rc, err = _run_ffmpeg([
                        "ffmpeg", "-y", "-analyzeduration", "200M", "-probesize", "200M",
                        "-fflags", "+discardcorrupt", "-err_detect", "ignore_err",
                        "-i", tmp_in, "-map", "0:v:0", "-c:v", "copy", "-f", "mpegts", ts_path,
                    ])
                    if rc != 0:
                        warnings.append(f"{rec.recording_id}: PS→TS copy failed, re-encoding")
                        rc, err = _run_ffmpeg([
                            "ffmpeg", "-y", "-analyzeduration", "200M", "-probesize", "200M",
                            "-fflags", "+genpts", "-i", tmp_in, "-map", "0:v:0",
                            "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
                            "-movflags", "+faststart", out_path,
                        ])
                    else:
                        rc, err = _run_ffmpeg([
                            "ffmpeg", "-y", "-analyzeduration", "200M", "-probesize", "200M",
                            "-i", ts_path, "-map", "0:v:0", "-c:v", "copy",
                            "-movflags", "+faststart", out_path,
                        ])
                        if rc != 0:
                            warnings.append(f"{rec.recording_id}: TS→MP4 copy failed, re-encoding")
                            rc, err = _run_ffmpeg([
                                "ffmpeg", "-y", "-analyzeduration", "200M", "-probesize", "200M",
                                "-fflags", "+genpts", "-i", ts_path, "-map", "0:v:0",
                                "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
                                "-movflags", "+faststart", out_path,
                            ])
                        if os.path.exists(ts_path):
                            os.remove(ts_path)

                    if rc == 0 and os.path.exists(out_path):
                        updated.append(dataclasses.replace(
                            rec, extracted_path=out_path, recovery_status="RECOVERED"
                        ))
                    else:
                        errors.append(f"{rec.recording_id}: extraction failed — {err.strip()[-300:]}")
                        updated.append(dataclasses.replace(rec, recovery_status="PARTIAL"))
                finally:
                    if os.path.exists(tmp_in):
                        os.remove(tmp_in)

        return ParseResult(
            vendor=self.vendor_name, parser_version=self.parser_version,
            success=len(errors) == 0,
            recordings=updated,
            warnings=warnings,
            errors=errors,
            error_code=ParseError.PARTIALLY_PARSED if errors else None,
        )