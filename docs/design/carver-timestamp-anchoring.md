# Forensic Disk Carver Timestamp Anchoring Design

## 1. Overview
`ForensicDiskCarverParser` (`backend/parsers/carver/parser.py`) carves video streams and containers from raw disk images where filesystem metadata is missing, wiped, or corrupted.

Currently, all carved recordings emit `original_timestamp = None` and `normalized_timestamp = None`. This document specifies the design for extracting absolute timestamps when available in the carved stream data, while strictly separating raw as-encoded timestamps from normalized timeline timestamps.

---

## 2. Stream Format Analysis & Absolute Timestamp Feasibility

| Stream Type | Absolute Timestamp Availability | Extraction Mechanism | Reliability / Confidence |
| :--- | :--- | :--- | :--- |
| **1. MP4 / MOV / 3GP** | **Yes** | Container header (`mvhd` / `tkhd` atom box `creation_time` field, seconds since Jan 1 1904 UTC). Extracted via `ffprobe` format tag `creation_time`. | **Low / Heuristic**: Vulnerable to camera RTC misconfiguration, epoch-zero (1904-01-01 / 1970-01-01), or future date corruption. |
| **2. MKV / EBML** | **Yes** | Segment Information element `DateUTC` (nanoseconds since Jan 1 2001 00:00:00 UTC). Extracted via `ffprobe` format tag `creation_time`. | **Low / Heuristic**: Same container date sanity checks required. |
| **3. DHAV (Dahua)** | **Yes** *(Unverified, needs real sample)* | 8-byte DHAV frame header encodes BCD/bit-packed camera RTC timestamp (Year, Month, Day, Hour, Min, Sec). | **Medium**: Local camera RTC timestamp; does not encode timezone offset. |
| **4. Raw H.264 (AVC)** | **Conditional** *(Unverified, needs real sample)* | Pic timing SEI or unregistered user data SEI (`NAL type 6`) inserted by IP encoders containing embedded camera RTC / UTC time. | **Medium**: Dependent on camera vendor SEI implementation. |
| **5. Raw H.265 (HEVC)** | **Conditional** *(Unverified, needs real sample)* | Time code SEI (`NAL type 39/40`) or vendor-specific user data SEI. | **Medium**: Dependent on camera vendor SEI implementation. |
| **6. AVI / RIFF** | **Conditional** | `LIST INFO` chunk `IDIT` (e.g., `"YYYY-MM-DD HH:MM:SS"` text) or `strh` chunk. Extracted via `ffprobe`. | **Low**: Textual string created by encoder software. |
| **7. MPEG-PS** | **No** | Pack header contains 33-bit System Clock Reference (SCR) which is a relative counter ($\approx 27\text{ MHz}$ / $90\text{ kHz}$ ticks), not an absolute calendar timestamp. | **None**: No absolute calendar timestamp exists in raw stream. |
| **8. FLV** | **No** | FLV tag headers contain millisecond offsets relative to stream start. | **None**: No absolute calendar timestamp exists in raw stream. |

---

## 3. Forensic Rules & Invariants

1. **`original_timestamp` Preservation**:
   * Stores the exact as-encoded timestamp extracted from the stream metadata or container atom.
   * **Never labeled as UTC unless the source format explicitly asserts UTC** (e.g. EBML `DateUTC` or ISO 8601 string with `Z`).
   * For local RTC timestamps without timezone (e.g., DHAV BCD headers or SEI packets), the timestamp is stored as a naive datetime or local-tagged datetime preserving raw values.

2. **`normalized_timestamp`**:
   * Stays `None` during the initial carve/parse phase.
   * Only populated later during investigative timeline normalization when time-zone offsets, camera drift, or reference anchor events are resolved.

3. **Container `creation_time` Validation & Rejection**:
   * Container creation dates are classified as **low confidence**.
   * Timestamps matching epoch-zero baselines must be rejected and left as `None`:
     * Jan 1, 1904 (`0` in QuickTime/MP4 epoch)
     * Jan 1, 1970 (`0` in Unix epoch)
     * Jan 1, 2001 (`0` in Matroska epoch)
   * Future dates ($> \text{current\_time} + 1\text{ day}$) must be rejected.
   * Ancient dates ($< \text{Jan 1, 2000}$) must be rejected for modern DVR recordings.

4. **Provenance Tracking in `raw_metadata`**:
   * When an absolute timestamp is anchored, `raw_metadata["timestamp_source"]` must be populated:
     * `"container_mvhd"`
     * `"ebml_date_utc"`
     * `"dhav_header"`
     * `"h264_sei_pic_timing"`
     * `"h265_sei_time_code"`
     * `"avi_idit_chunk"`
   * When unanchored or rejected, `raw_metadata["timestamp_source"]` must be `None`.
