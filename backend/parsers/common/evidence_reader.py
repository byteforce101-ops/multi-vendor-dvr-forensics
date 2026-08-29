"""Evidence source abstraction — preparation for .E01 / split-image support.

This module intentionally does NOT touch the existing Hikvision parser.
`backend/parsers/hikvision/parser.py` still reads its evidence file directly
via `mmap`, which is correct and efficient for raw .dd/.img files and must
keep working exactly as it does today.

.E01 (EnCase Evidence File Format) is NOT a raw disk image: it's a
compressed, checksummed container (with CRCs per chunk and an MD5/SHA1 hash
in the footer) that requires a proper decoder (e.g. via `pyewf`/`libewf`) to
turn "give me bytes at this offset" into real sector data — you cannot mmap
an .E01 file and expect raw-disk-image offsets to line up. Similarly, a
split raw image (`.001`, `.002`, ... or `evidence.dd.001`) is logically one
address space spread across multiple files on disk.

`EvidenceReader` is the common interface that lets a parser ask for
"offset X, length Y" without caring whether that maps to one mmap'd file,
a decoded E01 container, or a set of split segments. Parsers can be
migrated to depend on this abstraction instead of opening files directly
one at a time, once each concrete reader exists and is tested — see the
TODOs below for where that work plugs in.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class EvidenceReader(ABC):
    """Random-access read interface over a body of forensic evidence."""

    @abstractmethod
    def read(self, offset: int, size: int) -> bytes:
        """Return exactly `size` bytes starting at `offset`, or raise if the
        read would run past the end of the evidence."""
        ...

    @abstractmethod
    def get_size(self) -> int:
        """Total addressable size of the evidence, in bytes."""
        ...

    def __enter__(self) -> "EvidenceReader":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def close(self) -> None:  # pragma: no cover - default no-op
        ...


class RawImageReader(EvidenceReader):
    """EvidenceReader over a single raw .dd/.img file, via mmap.

    This is the one concrete reader implemented so far. It mirrors exactly
    the mmap-based access pattern `HikvisionParser` already uses internally
    (see backend/parsers/hikvision/parser.py), just exposed as a small
    reusable class instead of inline `mmap.mmap(...)` calls. The Hikvision
    parser has NOT been switched over to use this yet — that migration is
    left for a follow-up so the well-tested existing parser code path isn't
    disturbed here. New raw-image-based parsers can use this today.
    """

    def __init__(self, path: str):
        import mmap
        import os

        self._file = open(path, "rb")
        self._size = os.fstat(self._file.fileno()).st_size
        self._mmap = mmap.mmap(self._file.fileno(), 0, access=mmap.ACCESS_READ)

    def read(self, offset: int, size: int) -> bytes:
        if offset < 0 or size < 0 or offset + size > self._size:
            raise ValueError(
                f"Read out of bounds: offset={offset} size={size} total={self._size}"
            )
        return bytes(self._mmap[offset : offset + size])

    def get_size(self) -> int:
        return self._size

    def close(self) -> None:
        self._mmap.close()
        self._file.close()


class E01Reader(EvidenceReader):
    """Placeholder for EnCase (.E01/.Ex01) evidence file support.

    NOT IMPLEMENTED. Wiring this up requires a real EWF decoder (the
    `pyewf`/`libewf` bindings are the standard choice) to handle
    decompression, per-chunk CRC verification, and the segment-file table
    (.E01, .E02, ...) that makes up a single logical image. Do not attempt
    to treat an .E01 file as a raw image — the on-disk bytes are not sector
    data. This class exists so the intended integration point is explicit
    and discoverable; it deliberately raises until implemented.
    """

    def __init__(self, path: str):
        raise NotImplementedError(
            "E01Reader is not implemented yet. .E01 evidence requires an EWF "
            "decoder (e.g. pyewf/libewf) — see the module docstring in "
            "backend/parsers/common/evidence_reader.py."
        )

    def read(self, offset: int, size: int) -> bytes:  # pragma: no cover
        raise NotImplementedError

    def get_size(self) -> int:  # pragma: no cover
        raise NotImplementedError


class SplitImageReader(EvidenceReader):
    """Placeholder for split raw images (evidence.001, evidence.002, ...).

    NOT IMPLEMENTED. The real work here is building an index of
    (segment_path, start_offset_in_logical_image, size) tuples up front,
    then mapping a logical `read(offset, size)` across one or more
    underlying segment files/mmaps when a read straddles a segment
    boundary. Left unimplemented until there's a concrete fixture to test
    it against.
    """

    def __init__(self, segment_paths: list[str]):
        raise NotImplementedError(
            "SplitImageReader is not implemented yet — see the module "
            "docstring in backend/parsers/common/evidence_reader.py."
        )

    def read(self, offset: int, size: int) -> bytes:  # pragma: no cover
        raise NotImplementedError

    def get_size(self) -> int:  # pragma: no cover
        raise NotImplementedError
