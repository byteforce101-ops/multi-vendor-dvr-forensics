import hashlib
import os
from typing import Callable, Optional

CHUNK_SIZE = 8192

def compute_hashes(filepath: str) -> dict:
    sha256 = hashlib.sha256()
    md5 = hashlib.md5()
    with open(filepath, "rb") as f:
        while chunk := f.read(CHUNK_SIZE):
            sha256.update(chunk)
            md5.update(chunk)
    return {"sha256": sha256.hexdigest(), "md5": md5.hexdigest()}

def verify_hash(filepath: str, expected_sha256: str) -> bool:
    return compute_hashes(filepath)["sha256"] == expected_sha256


# Multi-gigabyte disk images make the 8 KiB default chunk size (and its lack
# of progress feedback) impractical for interactive tools. This variant is
# additive — compute_hashes/verify_hash above are untouched and still used
# by backend.core.acquisition.service — and is safe for arbitrarily large
# files since it never reads more than one chunk into memory at a time.
LARGE_FILE_CHUNK_SIZE = 8 * 1024 * 1024  # 8 MiB


def compute_hashes_with_progress(
    filepath: str,
    chunk_size: int = LARGE_FILE_CHUNK_SIZE,
    on_progress: Optional[Callable[[int, int], None]] = None,
) -> dict:
    """Stream-hash `filepath` in `chunk_size` chunks, reporting progress.

    `on_progress(bytes_read_so_far, total_bytes)` is called after every
    chunk if provided, so callers (e.g. a Rich progress bar) can render
    real, work-driven progress rather than a fake/simulated percentage.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than 0")

    total_bytes = os.path.getsize(filepath)
    sha256 = hashlib.sha256()
    md5 = hashlib.md5()
    bytes_read = 0

    with open(filepath, "rb") as f:
        while chunk := f.read(chunk_size):
            sha256.update(chunk)
            md5.update(chunk)
            bytes_read += len(chunk)
            if on_progress is not None:
                on_progress(bytes_read, total_bytes)

    return {"sha256": sha256.hexdigest(), "md5": md5.hexdigest(), "size": total_bytes}