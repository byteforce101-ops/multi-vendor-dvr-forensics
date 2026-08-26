"""
Generates a synthetic Hikvision-format disk image for testing.

This does NOT produce playable video — it only writes correct master block
and HIKBTREE index structures at the byte offsets our parser expects, so
detect()/validate()/parse() can be exercised without real hardware.
extract_recordings() will fail gracefully on this fixture (no real MPEG-PS
data) — that's expected and itself a useful test case.
"""

import struct
import os

SIGNATURE = b"HIKVISION@HANGZHOU"
HIKBTREE_SIGNATURE = b"HIKBTREE"
VERSION = b"HIK.2011.03.08"

DATA_BLOCK_SIZE = 1024 * 1024  # 1 MiB, small for a fast test fixture
HIKBTREE_PAGE_OFFSET = 0x400000  # arbitrary, past master block + headroom


def _u32(val: int) -> bytes:
    return struct.pack("<I", val)


def _u64(val: int) -> bytes:
    return struct.pack("<Q", val)


def _pad(buf: bytearray, target_len: int):
    if len(buf) < target_len:
        buf.extend(b"\x00" * (target_len - len(buf)))


def build_master_block(hikbtree_offset: int, total_blocks: int) -> bytes:
    block = bytearray(0x160)  # covers 0x200–0x360 relative region

    block[0x10:0x10 + len(SIGNATURE)] = SIGNATURE          # -> abs 0x210
    block[0x30:0x30 + len(VERSION)] = VERSION              # -> abs 0x230
    block[0x48:0x50] = _u64(500 * 1024 * 1024)              # capacity
    block[0x88:0x90] = _u64(DATA_BLOCK_SIZE)                # size_data_block
    block[0x90:0x94] = _u32(total_blocks)                   # total_data_blocks
    block[0x98:0xA0] = _u64(hikbtree_offset)                # offset_hibtree1
    block[0xF0:0xF4] = _u32(1_700_000_000)                  # time_system_init (unix ts)

    _pad(block, 0x160)
    return bytes(block)


def build_hbtree_page(entries: list[dict]) -> bytes:
    """One HIKBTREE page holding all our fake entries."""
    page = bytearray(0x60 + 48 * len(entries))
    page[0x10:0x14] = _u32(len(entries))              # entry_count
    page[0x20:0x28] = _u64(0xFFFFFFFFFFFFFFFF)         # next_page = end sentinel

    first_entry = 0x60
    for i, e in enumerate(entries):
        off = first_entry + i * 48
        page[off + 0x8:off + 0x10] = _u64(0)            # has_footage marker (0 = has footage)
        page[off + 0x11:off + 0x12] = bytes([e["channel"]])
        page[off + 0x18:off + 0x1C] = _u32(e["start_ts"])
        page[off + 0x1C:off + 0x20] = _u32(e["end_ts"])
        page[off + 0x20:off + 0x28] = _u64(e["datablock_offset"])
    return bytes(page)


def build_fixture(output_path: str):
    entries = [
        {"channel": 1, "start_ts": 1_700_000_100, "end_ts": 1_700_000_400,
         "datablock_offset": HIKBTREE_PAGE_OFFSET + 0x100000},
        {"channel": 2, "start_ts": 1_700_000_500, "end_ts": 1_700_000_900,
         "datablock_offset": HIKBTREE_PAGE_OFFSET + 0x200000},
        # one in-progress recording (dt1 == 0x7FFFFFFF -> "recording" branch)
        {"channel": 1, "start_ts": 0x7FFFFFFF, "end_ts": 0,
         "datablock_offset": HIKBTREE_PAGE_OFFSET + 0x300000},
    ]

    total_size = HIKBTREE_PAGE_OFFSET + 0x400000  # leave room past last data block
    image = bytearray(total_size)

    master = build_master_block(HIKBTREE_PAGE_OFFSET, total_blocks=len(entries))
    image[0x200:0x200 + len(master)] = master

    hbtree_header = bytearray(0x60)
    hbtree_header[0x10:0x18] = HIKBTREE_SIGNATURE
    hbtree_header[0x58:0x60] = _u64(HIKBTREE_PAGE_OFFSET + 0x60)  # offset_page
    image[HIKBTREE_PAGE_OFFSET:HIKBTREE_PAGE_OFFSET + len(hbtree_header)] = hbtree_header

    page = build_hbtree_page(entries)
    page_offset = HIKBTREE_PAGE_OFFSET + 0x60
    image[page_offset:page_offset + len(page)] = page

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(image)

    print(f"Wrote synthetic fixture: {output_path} ({len(image)} bytes)")
    print(f"Entries: {len(entries)} (2 completed recordings + 1 in-progress)")


if __name__ == "__main__":
    build_fixture("backend/tests/fixtures/hikvision_synthetic.dd")