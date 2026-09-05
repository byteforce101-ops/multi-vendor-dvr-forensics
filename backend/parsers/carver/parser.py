"""
Forensic Disk Image & Raw Stream Carver Parser.

Carves unallocated or multi-stream video containers (MP4, FLV, MPEG-PS, MPEG-TS,
AVI, MKV, DHAV, H.264/H.265) from raw disk images (.dd, .raw, .img, .bin, .dat, etc.)
where vendor-specific proprietary filesystem superblocks are wiped, corrupted, or absent.
"""

import json
import logging
import mmap
import os
import shutil
import struct
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from backend.parsers.common.base import (
    BaseDVRParser,
    NormalizedRecording,
    ParseError,
    ParseResult,
)

logger = logging.getLogger(__name__)

# Known MP4 major brands
MP4_BRANDS = {
    b"isom", b"iso2", b"avc1", b"mp41", b"mp42", b"3gp4", b"3gp5", b"3gp6",
    b"qt  ", b"M4V ", b"M4A ", b"f4v ", b"kddi", b"dash",
}


@dataclass
class CarvedStreamInfo:
    stream_type: str
    start_offset: int
    end_offset: int
    size_bytes: int
    description: str


def _parse_fps(rate_str: str) -> Optional[float]:
    try:
        if "/" in rate_str:
            num, denom = rate_str.split("/")
            return round(int(num) / int(denom), 2) if int(denom) != 0 else None
        return round(float(rate_str), 2)
    except Exception:
        return None


def probe_video_file(filepath: str) -> dict:
    """Probe a carved video file using ffprobe."""
    if not shutil.which("ffprobe"):
        return {}
    cmd = [
        "ffprobe",
        "-v", "error",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        str(filepath),
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if proc.returncode != 0 or not proc.stdout.strip():
            return {}
        info = json.loads(proc.stdout)
        vstream = next(
            (s for s in info.get("streams", []) if s.get("codec_type") == "video"),
            None,
        )
        fmt = info.get("format", {})
        duration = float(fmt.get("duration")) if fmt.get("duration") else None
        width = vstream.get("width") if vstream else None
        height = vstream.get("height") if vstream else None
        resolution = f"{width}x{height}" if width and height else None
        fps = _parse_fps(vstream.get("r_frame_rate", "")) if vstream else None
        codec = vstream.get("codec_name") if vstream else None
        file_size = int(fmt.get("size")) if fmt.get("size") else os.path.getsize(filepath)

        return {
            "duration_seconds": duration,
            "resolution": resolution,
            "fps": fps,
            "codec": codec,
            "file_size": file_size,
            "raw": info,
        }
    except Exception as exc:
        logger.debug(f"ffprobe failed for {filepath}: {exc}")
        return {}


def scan_carved_streams(data: bytes | mmap.mmap) -> list[CarvedStreamInfo]:
    """Scan raw disk buffer and locate video stream boundaries."""
    streams: list[CarvedStreamInfo] = []
    file_size = len(data)

    # 1. MP4 / MOV / 3GP
    pos = 0
    while True:
        p = data.find(b"ftyp", pos)
        if p == -1:
            break
        if p >= 4:
            box_start = p - 4
            brand = bytes(data[p + 4 : p + 8])
            if brand in MP4_BRANDS or any(b in brand for b in [b"mp4", b"iso", b"3gp", b"avc"]):
                # Parse MP4 top-level boxes
                cur = box_start
                while cur + 8 <= file_size:
                    bsize, btype = struct.unpack(">I4s", data[cur : cur + 8])
                    if bsize == 0:
                        cur = file_size
                        break
                    elif bsize == 1:
                        if cur + 16 > file_size:
                            break
                        bsize = struct.unpack(">Q", data[cur + 8 : cur + 16])[0]
                        cur += bsize
                    elif bsize < 8 or bsize > file_size - cur:
                        break
                    else:
                        try:
                            name = btype.decode("latin1")
                            if not all(c.isalnum() or c in " _-" for c in name):
                                break
                        except Exception:
                            break
                        cur += bsize
                        # Check padding termination
                        if cur + 4 <= file_size and data[cur : cur + 4] in (
                            b"\xb9\xb9\xb9\xb9", b"\x00\x00\x00\x00", b"\xff\xff\xff\xff",
                        ):
                            break

                mp4_len = cur - box_start
                if mp4_len >= 512:
                    streams.append(CarvedStreamInfo(
                        stream_type="mp4",
                        start_offset=box_start,
                        end_offset=cur,
                        size_bytes=mp4_len,
                        description=f"MP4/ISO Media Container ({brand.decode('latin1', 'replace')})",
                    ))
        pos = p + 4

    # 2. FLV
    pos = 0
    while True:
        p = data.find(b"FLV\x01", pos)
        if p == -1:
            break
        header_len = struct.unpack(">I", data[p + 5 : p + 9])[0] if p + 9 <= file_size else 9
        cur = p + header_len
        tags = 0
        while cur + 15 <= file_size:
            cur += 4  # prev tag size
            if cur + 11 > file_size:
                break
            tag_type = data[cur]
            if tag_type not in (8, 9, 18):
                cur -= 4
                break
            data_sz = (data[cur + 1] << 16) | (data[cur + 2] << 8) | data[cur + 3]
            total_tag_len = 11 + data_sz
            if cur + total_tag_len > file_size:
                cur -= 4
                break
            cur += total_tag_len
            tags += 1
            if cur + 4 <= file_size and data[cur : cur + 4] in (
                b"\xb9\xb9\xb9\xb9", b"\x00\x00\x00\x00", b"\xff\xff\xff\xff",
            ):
                break
        flv_len = cur - p
        if flv_len >= 512 and tags >= 1:
            streams.append(CarvedStreamInfo(
                stream_type="flv",
                start_offset=p,
                end_offset=cur,
                size_bytes=flv_len,
                description=f"Flash Video Stream ({tags} tags)",
            ))
        pos = p + 4

    # 3. MPEG-PS (0x000001BA packs)
    pos = 0
    ps_clusters: list[list[int]] = []
    while True:
        p = data.find(b"\x00\x00\x01\xba", pos)
        if p == -1:
            break
        if not ps_clusters or p - ps_clusters[-1][1] > 65536:
            ps_clusters.append([p, p, 1])
        else:
            ps_clusters[-1][1] = p
            ps_clusters[-1][2] += 1
        pos = p + 4

    for start_p, end_p, count in ps_clusters:
        if count >= 5:
            end_span = min(file_size, end_p + 2048)
            streams.append(CarvedStreamInfo(
                stream_type="mpeg_ps",
                start_offset=start_p,
                end_offset=end_span,
                size_bytes=end_span - start_p,
                description=f"MPEG-PS Surveillance Stream ({count} packs)",
            ))

    # 4. AVI / RIFF
    pos = 0
    while True:
        p = data.find(b"RIFF", pos)
        if p == -1:
            break
        if p + 12 <= file_size:
            riff_type = bytes(data[p + 8 : p + 12])
            if riff_type in (b"AVI ", b"AVIX"):
                riff_sz = struct.unpack("<I", data[p + 4 : p + 8])[0]
                end_span = min(file_size, p + 8 + riff_sz)
                streams.append(CarvedStreamInfo(
                    stream_type="avi",
                    start_offset=p,
                    end_offset=end_span,
                    size_bytes=end_span - p,
                    description="AVI Video Container",
                ))
        pos = p + 4

    # 5. MKV / EBML
    pos = 0
    while True:
        p = data.find(b"\x1a\x45\xdf\xa3", pos)
        if p == -1:
            break
        # MKV container header
        streams.append(CarvedStreamInfo(
            stream_type="mkv",
            start_offset=p,
            end_offset=min(file_size, p + 10 * 1024 * 1024),
            size_bytes=min(file_size - p, 10 * 1024 * 1024),
            description="Matroska (MKV) Container",
        ))
        pos = p + 4

    # 6. DHAV (Dahua)
    pos = 0
    dhav_clusters: list[list[int]] = []
    while True:
        p = data.find(b"DHAV", pos)
        if p == -1:
            p = data.find(b"dhav", pos)
            if p == -1:
                break
        if not dhav_clusters or p - dhav_clusters[-1][1] > 65536:
            dhav_clusters.append([p, p, 1])
        else:
            dhav_clusters[-1][1] = p
            dhav_clusters[-1][2] += 1
        pos = p + 4

    for start_p, end_p, count in dhav_clusters:
        if count >= 3:
            end_span = min(file_size, end_p + 4096)
            streams.append(CarvedStreamInfo(
                stream_type="dhav",
                start_offset=start_p,
                end_offset=end_span,
                size_bytes=end_span - start_p,
                description=f"Dahua DHAV Video Stream ({count} frames)",
            ))

    # 7. Deep Raw H.264 (AVC) Annex-B NAL Stream Carving
    # Look for 00 00 00 01 / 00 00 01 NAL start codes
    # SPS: 0x67/0x27/0x47, PPS: 0x68/0x28/0x48, IDR: 0x65/0x25/0x45
    h264_sps_pos = 0
    h264_clusters: list[list[int]] = []
    while True:
        p = data.find(b"\x00\x00\x00\x01\x67", h264_sps_pos)
        if p == -1:
            p = data.find(b"\x00\x00\x01\x67", h264_sps_pos)
        if p == -1:
            break

        # Scan forward for consecutive NAL units (PPS, IDR, slices)
        scan_cur = p + 4
        nal_count = 1
        has_idr = False
        last_nal = p
        while scan_cur + 5 <= file_size:
            next_start = data.find(b"\x00\x00\x00\x01", scan_cur)
            start_len = 4
            if next_start == -1 or next_start - last_nal > 2 * 1024 * 1024:
                alt = data.find(b"\x00\x00\x01", scan_cur)
                if alt != -1 and (next_start == -1 or alt < next_start):
                    next_start = alt
                    start_len = 3

            if next_start == -1 or next_start - last_nal > 2 * 1024 * 1024:
                break

            nal_type_byte = data[next_start + start_len]
            nal_type = nal_type_byte & 0x1F
            # Common H.264 NAL types: 1 (non-IDR slice), 5 (IDR), 6 (SEI), 7 (SPS), 8 (PPS), 9 (AUD)
            if nal_type in (1, 5, 6, 7, 8, 9):
                nal_count += 1
                if nal_type == 5:
                    has_idr = True
                last_nal = next_start
                scan_cur = next_start + start_len + 1
            else:
                # Stop if non-NAL sequence encountered
                break

        if nal_count >= 10 and has_idr:
            end_span = min(file_size, last_nal + 65536)
            h264_clusters.append([p, end_span, nal_count])
            h264_sps_pos = end_span
        else:
            h264_sps_pos = p + 4

    for start_p, end_p, count in h264_clusters:
        streams.append(CarvedStreamInfo(
            stream_type="h264",
            start_offset=start_p,
            end_offset=end_p,
            size_bytes=end_p - start_p,
            description=f"Raw H.264/AVC Elementary Stream ({count} NALs)",
        ))

    # 8. Deep Raw H.265 (HEVC) Annex-B NAL Stream Carving
    # VPS: 0x40/0x41 (type 32), SPS: 0x42/0x43 (type 33), PPS: 0x44/0x45 (type 34), IDR: 0x26/0x28 (type 19/20)
    hevc_pos = 0
    hevc_clusters: list[list[int]] = []
    while True:
        p = data.find(b"\x00\x00\x00\x01\x40", hevc_pos)
        if p == -1:
            p = data.find(b"\x00\x00\x00\x01\x42", hevc_pos)
        if p == -1:
            break

        scan_cur = p + 4
        nal_count = 1
        has_idr = False
        last_nal = p
        while scan_cur + 6 <= file_size:
            next_start = data.find(b"\x00\x00\x00\x01", scan_cur)
            if next_start == -1 or next_start - last_nal > 2 * 1024 * 1024:
                break
            nal_type = (data[next_start + 4] >> 1) & 0x3F
            # Types: 1 (TRAIL_R), 19/20 (IDR), 32 (VPS), 33 (SPS), 34 (PPS), 39/40 (SEI)
            if nal_type in (1, 2, 19, 20, 32, 33, 34, 39, 40):
                nal_count += 1
                if nal_type in (19, 20):
                    has_idr = True
                last_nal = next_start
                scan_cur = next_start + 5
            else:
                break

        if nal_count >= 8 and has_idr:
            end_span = min(file_size, last_nal + 65536)
            hevc_clusters.append([p, end_span, nal_count])
            hevc_pos = end_span
        else:
            hevc_pos = p + 4

    for start_p, end_p, count in hevc_clusters:
        streams.append(CarvedStreamInfo(
            stream_type="hevc",
            start_offset=start_p,
            end_offset=end_p,
            size_bytes=end_p - start_p,
            description=f"Raw H.265/HEVC Elementary Stream ({count} NALs)",
        ))

    # Sort and remove overlapping redundant slices
    streams.sort(key=lambda s: s.start_offset)
    unique_streams: list[CarvedStreamInfo] = []
    for s in streams:
        if not unique_streams:
            unique_streams.append(s)
        else:
            last = unique_streams[-1]
            if s.start_offset >= last.end_offset:
                unique_streams.append(s)
            elif s.size_bytes > last.size_bytes:
                unique_streams[-1] = s

    return unique_streams


class ForensicDiskCarverParser(BaseDVRParser):
    vendor_name = "generic_dvr_carver"
    parser_version = "0.1.0"

    def detect(self, evidence_path: str) -> tuple[bool, float, dict]:
        try:
            p = Path(evidence_path)
            if not p.exists() or not p.is_file():
                return False, 0.0, {}

            file_size = p.stat().st_size
            if file_size < 512:
                return False, 0.0, {}

            with open(evidence_path, "rb") as f:
                with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
                    streams = scan_carved_streams(mm)

            if streams:
                return True, 0.65, {
                    "vendor": self.vendor_name,
                    "streams_found": len(streams),
                    "stream_types": list({s.stream_type for s in streams}),
                    "total_carved_bytes": sum(s.size_bytes for s in streams),
                }

            return False, 0.0, {}
        except Exception as exc:
            logger.debug(f"Carver detect failed on {evidence_path}: {exc}")
            return False, 0.0, {}

    def validate(self, evidence_path: str) -> tuple[bool, list[str]]:
        warnings = []
        if not Path(evidence_path).is_file():
            return False, [f"Evidence file not found: {evidence_path}"]
        if shutil.which("ffmpeg") is None:
            warnings.append("ffmpeg not found on PATH — video remuxing may be limited.")
        return True, warnings

    def parse(self, evidence_path: str, output_directory: str) -> ParseResult:
        warnings: list[str] = []
        recordings: list[NormalizedRecording] = []
        out_dir = Path(output_directory)
        out_dir.mkdir(parents=True, exist_ok=True)

        try:
            with open(evidence_path, "rb") as f:
                with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
                    streams = scan_carved_streams(mm)

                    if not streams:
                        return ParseResult(
                            vendor=self.vendor_name,
                            parser_version=self.parser_version,
                            success=False,
                            error_code=ParseError.PARSE_FAILED,
                            errors=["No recognizable video streams found in disk image."],
                        )

                    for idx, s in enumerate(streams):
                        cam_num = idx + 1
                        rec_id = f"carved-{cam_num:03d}_{s.stream_type}"
                        raw_ext = f".{s.stream_type}" if s.stream_type in ("mp4", "flv", "avi", "mkv", "h264", "hevc") else ".bin"
                        raw_carved_path = out_dir / f"{rec_id}_raw{raw_ext}"
                        mp4_output_path = out_dir / f"{rec_id}.mp4"

                        # Write raw carved bytes
                        slice_bytes = mm[s.start_offset : s.end_offset]
                        with open(raw_carved_path, "wb") as rf:
                            rf.write(slice_bytes)

                        # Remux or copy to standard playable MP4
                        extracted_video_path = str(raw_carved_path)
                        if s.stream_type == "mp4":
                            # Direct MP4 container
                            extracted_video_path = str(raw_carved_path)
                            # Also ensure friendly name without _raw
                            if not mp4_output_path.exists():
                                shutil.copyfile(raw_carved_path, mp4_output_path)
                            extracted_video_path = str(mp4_output_path)
                        elif shutil.which("ffmpeg"):
                            # Remux to MP4
                            if s.stream_type in ("mpeg_ps", "dhav"):
                                rc = subprocess.run([
                                    "ffmpeg", "-y", "-analyzeduration", "200M", "-probesize", "200M",
                                    "-fflags", "+genpts", "-i", str(raw_carved_path),
                                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                                    "-movflags", "+faststart", str(mp4_output_path),
                                ], capture_output=True).returncode
                            elif s.stream_type == "h264":
                                rc = subprocess.run([
                                    "ffmpeg", "-y", "-f", "h264", "-analyzeduration", "200M", "-probesize", "200M",
                                    "-fflags", "+genpts", "-i", str(raw_carved_path),
                                    "-c:v", "copy", "-movflags", "+faststart", str(mp4_output_path),
                                ], capture_output=True).returncode
                                if rc != 0 or not mp4_output_path.exists() or mp4_output_path.stat().st_size == 0:
                                    rc = subprocess.run([
                                        "ffmpeg", "-y", "-f", "h264", "-analyzeduration", "200M", "-probesize", "200M",
                                        "-fflags", "+genpts", "-i", str(raw_carved_path),
                                        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                                        "-movflags", "+faststart", str(mp4_output_path),
                                    ], capture_output=True).returncode
                            elif s.stream_type == "hevc":
                                rc = subprocess.run([
                                    "ffmpeg", "-y", "-f", "hevc", "-analyzeduration", "200M", "-probesize", "200M",
                                    "-fflags", "+genpts", "-i", str(raw_carved_path),
                                    "-c:v", "copy", "-movflags", "+faststart", str(mp4_output_path),
                                ], capture_output=True).returncode
                                if rc != 0 or not mp4_output_path.exists() or mp4_output_path.stat().st_size == 0:
                                    rc = subprocess.run([
                                        "ffmpeg", "-y", "-f", "hevc", "-analyzeduration", "200M", "-probesize", "200M",
                                        "-fflags", "+genpts", "-i", str(raw_carved_path),
                                        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                                        "-movflags", "+faststart", str(mp4_output_path),
                                    ], capture_output=True).returncode
                            else:
                                rc = subprocess.run([
                                    "ffmpeg", "-y", "-i", str(raw_carved_path),
                                    "-c:v", "libx264", "-crf", "20", "-c:a", "aac",
                                    "-movflags", "+faststart", str(mp4_output_path),
                                ], capture_output=True).returncode

                            if rc == 0 and mp4_output_path.exists() and mp4_output_path.stat().st_size > 0:
                                extracted_video_path = str(mp4_output_path)

                        # Probe stream info
                        meta = probe_video_file(extracted_video_path)

                        recordings.append(NormalizedRecording(
                            camera_id=f"CH-{cam_num:02d}",
                            recording_id=rec_id,
                            source_path=evidence_path,
                            extracted_path=extracted_video_path,
                            original_timestamp=None,
                            normalized_timestamp=None,
                            duration_seconds=meta.get("duration_seconds"),
                            resolution=meta.get("resolution"),
                            fps=meta.get("fps"),
                            codec=meta.get("codec") or s.stream_type,
                            file_size=meta.get("file_size") or s.size_bytes,
                            recovery_status="RECOVERED",
                            device_model=s.description,
                            raw_metadata={
                                "stream_type": s.stream_type,
                                "start_offset": s.start_offset,
                                "end_offset": s.end_offset,
                                "size_bytes": s.size_bytes,
                                "description": s.description,
                                "probe": meta.get("raw", {}),
                            },
                        ))

            return ParseResult(
                vendor=self.vendor_name,
                parser_version=self.parser_version,
                success=True,
                recordings=recordings,
                warnings=warnings,
                raw_master_block={"carved_streams_count": len(recordings)},
            )
        except Exception as exc:
            return ParseResult(
                vendor=self.vendor_name,
                parser_version=self.parser_version,
                success=False,
                error_code=ParseError.PARSE_FAILED,
                errors=[str(exc)],
            )

    def extract_recordings(
        self,
        evidence_path: str,
        output_directory: str,
        recordings: list[NormalizedRecording],
        raw_master_block: object | None,
    ) -> ParseResult:
        """Ensure all recordings are properly extracted to output_directory."""
        updated: list[NormalizedRecording] = []
        for rec in recordings:
            if rec.extracted_path and Path(rec.extracted_path).is_file():
                updated.append(rec)
            else:
                # If not extracted yet, re-run parse to populate
                res = self.parse(evidence_path, output_directory)
                return res
        return ParseResult(
            vendor=self.vendor_name,
            parser_version=self.parser_version,
            success=True,
            recordings=updated,
            raw_master_block=raw_master_block,
        )
