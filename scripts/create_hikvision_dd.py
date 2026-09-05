"""scripts/create_hikvision_dd.py — Generate synthetic Hikvision .dd disk images from video files.

Creates valid Hikvision DVR filesystem disk images (Master Block + HIKBTREE index + MPEG-PS data blocks)
that can be detected, parsed, and carved by the TraceX Hikvision parser.
"""

import argparse
import os
import shutil
import struct
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

SIGNATURE = b"HIKVISION@HANGZHOU"
HIKBTREE_SIGNATURE = b"HIKBTREE"
KNOWN_GOOD_VERSION = b"HIK.2011.03.08"


def _u32(val: int) -> bytes:
    return struct.pack("<I", int(val))


def _u64(val: int) -> bytes:
    return struct.pack("<Q", int(val))


def create_hikvision_dd_from_video(
    video_path: str | Path,
    output_dd_path: str | Path,
    channel: int = 1,
    start_time: datetime | None = None,
    duration_seconds: int | None = None,
) -> Path:
    video_file = Path(video_path).expanduser().resolve()
    if not video_file.is_file():
        raise FileNotFoundError(f"Input video file not found: {video_file}")

    out_dd = Path(output_dd_path).expanduser().resolve()
    out_dd.parent.mkdir(parents=True, exist_ok=True)

    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg is required on PATH to multiplex video into MPEG-PS format.")

    print(f"[*] Ingesting video: {video_file} ({video_file.stat().st_size:,} bytes)")

    # 1. Convert video to MPEG-PS format compatible with Hikvision DVR stream structure
    temp_dir = Path(tempfile.mkdtemp(prefix="tracex_hik_"))
    ps_temp = temp_dir / "stream.ps"

    try:
        print("[*] Transcoding video to Hikvision-compatible MPEG-PS program stream...")
        cmd = [
            "ffmpeg", "-y",
            "-i", str(video_file),
            "-c:v", "mpeg2video",
            "-b:v", "4M",
            "-f", "vob",
            str(ps_temp),
        ]
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        if res.returncode != 0 or not ps_temp.is_file():
            err_msg = res.stderr.decode("utf-8", "ignore")
            raise RuntimeError(f"ffmpeg failed to create MPEG-PS stream: {err_msg}")

        ps_data = ps_temp.read_bytes()
        ps_size = len(ps_data)
        print(f"[*] Generated MPEG-PS payload: {ps_size:,} bytes")

        # 2. Disk Layout Offsets
        HIKBTREE_OFFSET = 0x400000  # 4 MiB
        DATA_BLOCK_OFFSET = 0x500000  # 5 MiB
        DATA_BLOCK_SIZE = max(ps_size + 1024 * 1024, 32 * 1024 * 1024)

        if start_time is None:
            start_ts = int(datetime(2024, 5, 12, 14, 23, 10, tzinfo=timezone.utc).timestamp())
        else:
            start_ts = int(start_time.timestamp())

        dur = duration_seconds if duration_seconds is not None else 38
        end_ts = start_ts + dur

        total_disk_size = DATA_BLOCK_OFFSET + ps_size + 4096
        image = bytearray(total_disk_size)

        # 3. Master Block at 0x200..0x360
        master = bytearray(0x160)
        master[0x10:0x10 + len(SIGNATURE)] = SIGNATURE
        master[0x30:0x30 + len(KNOWN_GOOD_VERSION)] = KNOWN_GOOD_VERSION
        master[0x48:0x50] = _u64(500 * 1024 * 1024)  # 500 MB capacity
        master[0x88:0x90] = _u64(DATA_BLOCK_SIZE)     # size_data_block
        master[0x90:0x94] = _u32(1)                   # total_data_blocks
        master[0x98:0xA0] = _u64(HIKBTREE_OFFSET)     # offset_hibtree1
        master[0xF0:0xF4] = _u32(start_ts - 3600)     # time_system_init
        image[0x200:0x200 + len(master)] = master

        # 4. HIKBTREE Header at HIKBTREE_OFFSET
        hbtree_hdr = bytearray(0x60)
        hbtree_hdr[0x10:0x18] = HIKBTREE_SIGNATURE
        hbtree_hdr[0x58:0x60] = _u64(HIKBTREE_OFFSET + 0x60)
        image[HIKBTREE_OFFSET:HIKBTREE_OFFSET + len(hbtree_hdr)] = hbtree_hdr

        # 5. HIKBTREE Page at HIKBTREE_OFFSET + 0x60
        page = bytearray(0x60 + 48)
        page[0x10:0x14] = _u32(1)                     # entry_count = 1
        page[0x20:0x28] = _u64(0xFFFFFFFFFFFFFFFF)    # end of tree sentinel

        off = 0x60
        page[off + 0x8:off + 0x10] = _u64(0)          # has_footage = 0 (footage present)
        page[off + 0x11:off + 0x12] = bytes([channel]) # Camera Channel
        page[off + 0x18:off + 0x1C] = _u32(start_ts)  # start timestamp
        page[off + 0x1C:off + 0x20] = _u32(end_ts)    # end timestamp
        page[off + 0x20:off + 0x28] = _u64(DATA_BLOCK_OFFSET)
        image[HIKBTREE_OFFSET + 0x60:HIKBTREE_OFFSET + 0x60 + len(page)] = page

        # 6. Data Block at DATA_BLOCK_OFFSET
        image[DATA_BLOCK_OFFSET:DATA_BLOCK_OFFSET + ps_size] = ps_data

        # Write final .dd image
        out_dd.write_bytes(image)
        print(f"[✔] Successfully created synthetic Hikvision .dd disk image:")
        print(f"    Path: {out_dd}")
        print(f"    Size: {len(image):,} bytes ({len(image) / (1024*1024):.2f} MB)")
        print(f"    Channel: CH-{channel:02d}")
        print(f"    Timestamp: {datetime.fromtimestamp(start_ts, tz=timezone.utc).isoformat()} UTC")

        return out_dd

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def main():
    parser = argparse.ArgumentParser(description="Generate synthetic Hikvision .dd disk images from video files.")
    parser.add_argument("input_video", help="Path to input video file (e.g. .mp4)")
    parser.add_argument("-o", "--output", default="hikvision_synthetic_dashcam.dd", help="Output .dd image path")
    parser.add_argument("-c", "--channel", type=int, default=1, help="Camera channel number (default: 1)")

    args = parser.parse_args()
    create_hikvision_dd_from_video(args.input_video, args.output, channel=args.channel)


if __name__ == "__main__":
    main()
