"""
Generate synthetic Hikvision forensic disk images (.dd) from a real CCTV MP4 video.

Generates two .dd disk images:
1. `hikvision_normal.dd`: A valid Hikvision disk image with Master Block and HIKBTREE index
   pointing to the video data block(s) -> extracted with recovery_status="ORIGINAL".
2. `hikvision_deleted.dd`: A valid Hikvision disk image where the video data blocks exist
   in unallocated sectors, but the HIKBTREE index has been wiped/cleared -> recovered with recovery_status="RECOVERED".
"""

import os
import shutil
import struct
import subprocess
import tempfile
import time
from pathlib import Path

SIGNATURE = b"HIKVISION@HANGZHOU"
HIKBTREE_SIGNATURE = b"HIKBTREE"
KNOWN_GOOD_VERSION = b"HIK.2011.03.08"
BA_NAL = bytes.fromhex("00000001BA")

SOURCE_VIDEO = r"C:\Users\sarthak\Downloads\hd-cctv-camera-video-3mp-4mp-iprox-cctv-hdcctvcameras-net-retail-store-ytmp4.savetube.vip.mp4"


def convert_mp4_to_mpeg_ps(input_mp4: str, output_ps: str, duration_sec: int = 45) -> bool:
    """Convert input MP4 video into an MPEG-PS surveillance stream with BA_NAL packs."""
    cmd = [
        "ffmpeg", "-y",
        "-t", str(duration_sec),
        "-i", input_mp4,
        "-c:v", "mpeg2video",
        "-b:v", "4000k",
        "-maxrate", "5000k",
        "-bufsize", "2000k",
        "-an",
        "-f", "dvd",
        output_ps,
    ]
    res = subprocess.run(cmd, capture_output=True)
    return res.returncode == 0 and os.path.exists(output_ps) and os.path.getsize(output_ps) > 0


def build_hikvision_disk_image(
    output_dd_path: str,
    ps_video_path: str,
    is_deleted: bool = False,
    channel: int = 1,
    start_ts: int = 1718000000,
    end_ts: int = 1718000100,
):
    """Construct a full Hikvision disk image (.dd)."""
    with open(ps_video_path, "rb") as f:
        ps_data = f.read()

    ps_len = len(ps_data)
    # Ensure BA pack is at the beginning
    if not ps_data.startswith(BA_NAL):
        idx = ps_data.find(BA_NAL)
        if idx != -1:
            ps_data = ps_data[idx:]
            ps_len = len(ps_data)

    # 1. Geometry and offsets
    size_data_block = 8 * 1024 * 1024  # 8 MB per block
    total_data_blocks = 4
    offset_hibtree1 = 0x1000  # 4096
    offset_page = 0x2000      # 8192
    offset_datablock_1 = 0x100000  # 1MB

    total_image_size = offset_datablock_1 + (total_data_blocks * size_data_block)  # 33 MB

    image = bytearray(b"\x00" * total_image_size)

    # 2. Master Block at 0x200 (length 0x160)
    # 0x200 + 0x10 = 0x210: Signature (18 bytes)
    image[0x210 : 0x210 + len(SIGNATURE)] = SIGNATURE
    # 0x200 + 0x30 = 0x230: Version (14 bytes)
    image[0x230 : 0x230 + len(KNOWN_GOOD_VERSION)] = KNOWN_GOOD_VERSION
    # 0x200 + 0x48 = 0x248: capacity (uint64)
    struct.pack_into("<Q", image, 0x248, total_image_size)
    # 0x200 + 0x88 = 0x288: size_data_block (uint64)
    struct.pack_into("<Q", image, 0x288, size_data_block)
    # 0x200 + 0x90 = 0x290: total_data_blocks (uint32)
    struct.pack_into("<I", image, 0x290, total_data_blocks)
    # 0x200 + 0x98 = 0x298: offset_hibtree1 (uint64)
    struct.pack_into("<Q", image, 0x298, offset_hibtree1)
    # 0x200 + 0xF0 = 0x2F0: time_system_init (uint32)
    struct.pack_into("<I", image, 0x2F0, int(time.time()) - 86400 * 30)

    # 3. HIKBTREE Header at offset_hibtree1 (0x1000)
    image[offset_hibtree1 + 0x10 : offset_hibtree1 + 0x10 + len(HIKBTREE_SIGNATURE)] = HIKBTREE_SIGNATURE
    struct.pack_into("<Q", image, offset_hibtree1 + 0x58, offset_page)

    # 4. HIKBTREE Page at offset_page (0x2000)
    struct.pack_into("<Q", image, offset_page + 0x20, 0xFFFFFFFFFFFFFFFF)  # next_page = last

    if not is_deleted:
        # Active Normal Recording in Index
        entry_count = 1
        struct.pack_into("<I", image, offset_page + 0x10, entry_count)
        first_entry = offset_page + 0x60
        # Entry layout (48 bytes):
        # +0x08: uint64 0 (has footage)
        struct.pack_into("<Q", image, first_entry + 0x08, 0)
        # +0x11: uint8 channel
        struct.pack_into("B", image, first_entry + 0x11, channel)
        # +0x18: uint32 start_timestamp
        struct.pack_into("<I", image, first_entry + 0x18, start_ts)
        # +0x1C: uint32 end_timestamp
        struct.pack_into("<I", image, first_entry + 0x1C, end_ts)
        # +0x20: uint64 offset_datablock
        struct.pack_into("<Q", image, first_entry + 0x20, offset_datablock_1)
    else:
        # Deleted footage: entry_count = 0 in B-Tree index (or B-Tree cleared)
        # The data block remains intact in unallocated space at offset_datablock_1
        struct.pack_into("<I", image, offset_page + 0x10, 0)

    # 5. Populate Data Block with Video Stream
    write_len = min(ps_len, size_data_block)
    image[offset_datablock_1 : offset_datablock_1 + write_len] = ps_data[:write_len]

    # Save disk image
    os.makedirs(os.path.dirname(os.path.abspath(output_dd_path)), exist_ok=True)
    with open(output_dd_path, "wb") as out_f:
        out_f.write(image)

    print(f"Generated {output_dd_path} ({len(image) / (1024*1024):.1f} MB) - Deleted={is_deleted}")


def main():
    if not os.path.exists(SOURCE_VIDEO):
        print(f"Error: Source video not found: {SOURCE_VIDEO}")
        return

    temp_ps = tempfile.mktemp(suffix=".ps")
    try:
        print(f"Converting source CCTV MP4 to MPEG-PS stream...")
        ok = convert_mp4_to_mpeg_ps(SOURCE_VIDEO, temp_ps, duration_sec=45)
        if not ok:
            print("Failed to convert MP4 to MPEG-PS.")
            return

        # Output paths
        storage_orig = Path("backend/storage/original")
        storage_orig.mkdir(parents=True, exist_ok=True)

        normal_path = str(storage_orig / "hikvision_normal.dd")
        deleted_path = str(storage_orig / "hikvision_deleted.dd")

        print("Building normal Hikvision disk image...")
        build_hikvision_disk_image(normal_path, temp_ps, is_deleted=False, channel=1)

        print("Building deleted-footage Hikvision disk image...")
        build_hikvision_disk_image(deleted_path, temp_ps, is_deleted=True, channel=1)

        # Also copy to fixtures for tests
        fixtures_dir = Path("backend/tests/fixtures")
        fixtures_dir.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(normal_path, fixtures_dir / "hikvision_normal.dd")
        shutil.copyfile(deleted_path, fixtures_dir / "hikvision_deleted.dd")

        print("Successfully generated all Hikvision forensic images.")
    finally:
        if os.path.exists(temp_ps):
            os.remove(temp_ps)


if __name__ == "__main__":
    main()
