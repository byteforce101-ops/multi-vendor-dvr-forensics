# Standard Operating Procedures (SOPs)
## Multi-Vendor DVR/NVR Forensic Analysis Platform

---

## SOP-01: Evidence Acquisition

**Purpose:** Standardize how DVR/NVR hard drives are imaged and registered in the system to ensure evidence admissibility.

**Pre-requisites:**
- Forensic write blocker connected between HDD and workstation
- `dd` or forensic imaging tool available
- MD5/SHA-256 hash utilities available

### Steps

1. **Power down the DVR/NVR** before removing the hard drive. Do NOT allow the device to continue recording — circular buffer overwrites destroy evidence.

2. **Connect with write blocker.** Use a hardware write blocker (e.g., Tableau TE8, UltraBlock) between the drive and your forensic workstation.

3. **Create a forensic image:**
   ```bash
   dd if=/dev/sdX of=/evidence/case_001/exhibit_A.dd bs=512 conv=noerror,sync status=progress
   ```

4. **Compute hash immediately after imaging:**
   ```bash
   sha256sum /evidence/case_001/exhibit_A.dd > /evidence/case_001/exhibit_A.dd.sha256
   md5sum /evidence/case_001/exhibit_A.dd > /evidence/case_001/exhibit_A.dd.md5
   ```

5. **Create a case and register evidence in the platform:**
   ```bash
   dvr-forensics case create --name "Case 001" --investigator "Agent Name"
   dvr-forensics evidence add --case-id <id> --path /evidence/case_001/exhibit_A.dd
   ```

6. **Verify hash after ingest** (platform re-computes and stores SHA-256 automatically).

**Documentation required:** Chain-of-custody form, acquisition log with timestamps, write-blocker model/serial.

---

## SOP-02: Vendor Detection

**Purpose:** Identify which DVR/NVR manufacturer produced the evidence before attempting parse.

### Steps

1. **Run the detect command:**
   ```bash
   dvr-forensics detect /evidence/case_001/exhibit_A.dd
   ```

2. **Review the candidate table output:**
   - Candidates are ranked by confidence score (0.0–1.0)
   - The winning parser (highest confidence + `matched=True`) is shown at top
   - Skipped parsers (outscored by winner) are listed with reason
   - Hex dump and ASCII strings of the first 256 bytes are displayed

3. **Confirm the vendor match is correct** based on physical device label, serial number, and/or case notes.

4. **If vendor is unexpected:** Run with `--exhaustive` flag to try all parsers:
   ```bash
   dvr-forensics detect /evidence/case_001/exhibit_A.dd --exhaustive
   ```

**Confidence thresholds:**
| Score | Interpretation |
|---|---|
| ≥ 0.85 | High confidence — binary signature match (proceed to parse) |
| 0.70–0.84 | Moderate — brand string + stream match (proceed with caution) |
| 0.60–0.69 | Low — brand-only match (validate physically before parsing) |
| < 0.60 | Do not use specific parser — use generic carver |

---

## SOP-03: Evidence Parsing

**Purpose:** Extract structured recording metadata from a detected evidence file.

### Steps

1. **Run parse with detected vendor:**
   ```bash
   dvr-forensics parse /evidence/case_001/exhibit_A.dd --output /evidence/case_001/extracted/
   ```

2. **Review parse output:**
   - Number of recordings found
   - Per-recording: camera ID, timestamp, duration, resolution, codec
   - Any warnings (e.g., "partial frame scan", "UBS index not decoded")

3. **Note all warnings** in case documentation. Warnings do not invalidate evidence but must be disclosed.

4. **Verify evidence hash unchanged** — the platform automatically re-verifies SHA-256 post-parse. Any hash mismatch is a critical error.

---

## SOP-04: Video Extraction

**Purpose:** Remux proprietary DVR recordings to standard, court-admissible MP4 files.

### Steps

1. **Extract recordings:**
   ```bash
   dvr-forensics extract /evidence/case_001/exhibit_A.dd --output /evidence/case_001/extracted/
   ```

2. **Verify extraction output:**
   - Each MP4 in output directory corresponds to one camera channel / recording segment
   - Filename includes `recording_id` linking back to the parse result in the database

3. **Hash extracted files:**
   ```bash
   sha256sum /evidence/case_001/extracted/*.mp4 >> /evidence/case_001/extraction_hashes.txt
   ```

4. **Do NOT re-encode unnecessarily.** The platform uses stream copy (`-c:v copy`) as first strategy. Re-encoding is only used as a last resort and is documented in warnings.

---

## SOP-05: AI Analysis

**Purpose:** Detect persons, vehicles, and events in extracted video for investigative leads.

### Steps

1. **Run AI analysis on an extracted MP4:**
   ```bash
   dvr-forensics analyze /evidence/case_001/extracted/hikvision-ch01-0000.mp4
   ```

2. **Review output:**
   - Entity trajectory timeline (track IDs, classes, direction, speed)
   - Critical forensic alerts (loitering, sudden disappearance, flagged events)
   - Executive forensic narrative summary

3. **AI analysis is investigative only** — it produces leads, not legal proof. All AI flags must be confirmed by a qualified human analyst before court submission.

---

## SOP-06: Report Generation

**Purpose:** Generate a standardized forensic report for case documentation and court submission.

### Steps

1. **Generate report via API:**
   ```
   GET /api/evidence/{evidence_id}/report
   ```

2. **Report includes:**
   - Case metadata (case name, investigator, date)
   - Evidence file details (path, size, SHA-256, MD5)
   - Detection result (vendor, confidence, detection info)
   - Parse results (recording count, channels, timestamps)
   - Extraction results (output paths, per-file hashes)
   - Warnings and error log
   - Chain-of-custody timeline

3. **Review and sign report** before submission to court or legal team.

---

## SOP-07: Deleted Video Recovery

**Purpose:** Attempt recovery of recordings deleted or overwritten by the DVR's circular buffer.

> ⚠️ **WARNING:** Deleted recovery is best-effort only. Success depends on whether the physical disk blocks have been overwritten. Stop the DVR from recording immediately on seizure.

### Steps

1. **For Hikvision:** The platform's Hikvision parser automatically attempts to recover deleted recording blocks by traversing the HIKBTREE index for blocks marked "deleted" but not yet overwritten.

2. **For Dahua / CP Plus / Godrej (Dahua line):** DHAV frame carving in the scan window will recover frames that remain physically on disk even if the DHFS index has been cleared.

3. **For Honeywell:** Use `eraw1am/Honeywell-NVR-Filesystem-Tools/dat_carving.py` as supplemental tool (documented in DFRWS 2026 paper arXiv:2605.07430).

4. **For all brands:** Run `dvr-forensics parse` — any NormalizedRecording with `recovery_status="RECOVERED"` was retrieved from unindexed or partially overwritten space.

---

*SIH 2026 — Problem Statement SIH26150*
*Multi-Vendor DVR/NVR Forensic Analysis Platform*
