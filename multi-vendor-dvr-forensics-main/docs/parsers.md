# Vendor Parser Documentation

## Architecture

All vendor parsers implement `BaseDVRParser` (backend/parsers/common/base.py):
- `detect(evidence_path) -> (bool, confidence, device_info)` — signature/structure sniffing
- `validate(evidence_path) -> (bool, warnings)` — checks the evidence is well-formed before parsing
- `parse(evidence_path, output_directory) -> ParseResult` — extracts metadata, returns normalized recordings
- `extract_recordings(...) -> ParseResult` — muxes/exports actual video where supported

`ParserManager` (backend/parsers/registry.py) tries each registered parser's `detect()`
and dispatches to whichever reports the highest confidence match. The generic
FFprobe-based parser is registered last and matches any standard container
(MP4/AVI/MKV) as a low-confidence fallback.

## Supported Vendors

### Hikvision
- **Status:** Metadata extraction (master block + HIKBTREE index parsing) implemented
  and validated against a synthetic structural fixture
  (`backend/tests/fixtures/hikvision_synthetic.dd`). **Not yet validated against
  real hardware or a real disk image.**
- **Confirmed filesystem version:** `HIK.2011.03.08` (per the reference implementation).
  Other versions are accepted but flagged with a warning — offsets may not match,
  results are unverified.
- **Scope:** operates on raw disk images (`.dd`), not vendor export folders. Detects
  via the `HIKVISION@HANGZHOU` master block signature at a fixed offset.
- **Extraction:** attempts to mux MPEG-PS video data into MP4 via ffmpeg. Recordings
  that fail to mux (no MPEG-PS start code found, empty/zeroed data block, missing
  offset, ffmpeg failure) are demoted to `recovery_status: "PARTIAL"` rather than
  silently dropped or falsely marked as recovered.
- **Known gaps:**
  - IDR entry/header parsing is not implemented (the reference implementation this
    was adapted from also left it non-functional).
  - No raw H.264 elementary-stream export option — MP4 mux only, by design choice.
  - Physical-order/channel-filter options from the reference CLI were not ported;
    can be added to `parse()`/`extract_recordings()` later if needed.
- **Adapted from:** [fmpfeifer/hikextractor](https://github.com/fmpfeifer/hikextractor).
  Master block and HIKBTREE struct offsets, and the overall parsing approach, are
  derived from that project. License terms: [record status here — confirm before
  distribution].

### Dahua
- **Status:** Not yet implemented.

### Generic (fallback)
- **Status:** Implemented and functional.
- **Scope:** any standard MP4/AVI/MKV container. Uses ffprobe for codec, resolution,
  fps, duration, and file size. No proprietary parsing — used when no vendor-specific
  parser matches (e.g., a vendor export that's a plain video file with sidecar
  metadata, rather than a proprietary container).

## Adding a new vendor parser

1. Create `backend/parsers/<vendor>/parser.py`.
2. Implement a class extending `BaseDVRParser` with `detect`, `validate`, `parse`,
   and optionally `extract_recordings`.
3. Register the parser instance in `PARSERS` in `backend/parsers/registry.py`,
   ordered before the generic fallback.
4. Document supported versions/known gaps in this file, following the format above.
5. Never claim support for a format/version you haven't actually tested — flag
   unverified versions as warnings, not silent successes.

## Testing philosophy

Where real hardware/disk images aren't available, parsers are validated against
synthetic fixtures that replicate the expected byte structure
(see `backend/tests/fixtures/`). This proves the parsing *logic* is correct against
a known-good structural layout, but does **not** prove real-world compatibility
with actual DVR firmware. This distinction is called out per-vendor above and
should be preserved in any report or demo — "validated against synthetic fixture"
is a different, weaker claim than "tested against real hardware," and conflating
them would misrepresent what's actually been proven.