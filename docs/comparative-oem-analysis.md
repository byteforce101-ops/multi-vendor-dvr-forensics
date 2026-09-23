# Comparative Analysis of Major DVR/NVR OEMs
## Multi-Vendor DVR/NVR Forensic Analysis Platform — SIH 2026 (SIH26150)

---

## 1. Executive Summary

This document provides a forensically rigorous comparative analysis of the eight major DVR/NVR manufacturers targeted by this platform: **Dahua Technology, CP Plus, Honeywell Security, TP-Link, Godrej Security Solutions, Uniview, Hikvision, and Matrix Comsec**. It covers disk filesystem architecture, proprietary recording formats, video codecs, forensic recovery difficulty, and OEM relationships — the information required for legally defensible evidence acquisition and admissibility.

---

## 2. OEM Relationship Map

Understanding OEM lineage is essential in forensic examination: evidence attributed to "CP Plus" must be traced to its actual firmware and disk format to select the correct parsing method.

```
Dahua Technology (DHFS4.1 + DHAV)
├── CP Plus (Aditya Infotech) — Full OEM rebadge
│   └── Uses DHFS4.1 filesystem, DHAV frame containers, port 37777
├── Godrej Security (STE-UR / STE-NVR line) — Dahua OEM
│   └── Uses DHFS4.1 filesystem, DHAV frame containers
└── TP-Link Vigi NVR — DHAV recording format (ext4 filesystem)

Hikvision (HIKVISION@HANGZHOU superblock)
└── Honeywell Performance Series HRGX — Legacy Hikvision OEM (pre-2021)

Xiongmai / XMEye (Sofia firmware, AA55AA55 sync)
└── Godrej Security (SeeThru Eco / ACE line) — Xiongmai OEM

Indigenous Manufacturers (proprietary formats)
├── Hikvision — HKFS + HIKBTREE + MPEG-PS
├── Honeywell — Proprietary 20-byte NAL header + block index (2-partition FS)
├── Matrix Comsec — SATATYA (.stm / .mxs / .avs) — genuinely independent
└── Uniview — UBS (Universal Block Storage) — genuinely independent
```

---

## 3. Per-Brand Technical Profile

### 3.1 Hikvision

| Property | Detail |
|---|---|
| **Headquarters** | Hangzhou, China (subsidiary of CETC) |
| **Market share** | #1 globally (IP camera + DVR) |
| **Disk filesystem** | Proprietary HKFS with `HIKBTREE` B-tree index |
| **Superblock signature** | `HIKVISION@HANGZHOU` at sector 0 (18 bytes) |
| **Frame format** | MPEG-PS (`.mts`) with IMKH/HK40 markers |
| **Primary codecs** | H.264 AVC, H.265 HEVC, Hikvision H.264+ / H.265+ |
| **Export formats** | `.mp4`, `.avi`, `.dav` |
| **Deleted recovery** | Recoverable via master sector + HIKBTREE index traversal |
| **Forensic tools** | `hikextractor` (open-source), Magnet DVR Examiner |
| **NDAA compliance** | Section 889 restricted (federal procurement banned) |
| **Accuracy in platform** | ✅ High — tested on real `.dd` fixture |

### 3.2 Dahua Technology

| Property | Detail |
|---|---|
| **Headquarters** | Hangzhou, China |
| **Market share** | #2 globally |
| **Disk filesystem** | DHFS (Dahua File System) v4.0 / v4.1 |
| **Superblock signature** | `DHFS4.1` at sector 0 (7 bytes: `44 48 46 53 34 2E 31`) |
| **Frame format** | DHAV — per-frame container with `DHAV`/`dhav` header/footer |
| **Frame magic bytes** | `44 48 41 56` (DHAV) or `44 41 48 55 41` (DAHUA) at byte 0 |
| **Timestamp encoding** | 32-bit packed bitfield: year(6b), month(4b), day(5b), hr(5b), min(6b), sec(6b) |
| **Primary codecs** | H.264, H.265, Smart H.264+/H.265+ |
| **Export formats** | `.dav`, FFmpeg-remuxable to `.mp4` |
| **Deleted recovery** | Circular buffer — overwritten blocks not recoverable; intact frames recoverable |
| **Forensic tools** | `gbatmobile/dhfs_extractor`, `DmytroMoisiuk/DVR_Dahua`, FFmpeg native |
| **Accuracy in platform** | ✅ High detection (FFmpeg source verified); no real disk fixture tested |

### 3.3 CP Plus (Aditya Infotech Ltd.)

| Property | Detail |
|---|---|
| **Headquarters** | Noida, India |
| **Market position** | #1 in India by volume |
| **OEM relationship** | **Dahua Technology OEM** (full hardware + firmware rebadge) |
| **Disk filesystem** | DHFS4.1 (identical to Dahua) |
| **Frame format** | DHAV (identical to Dahua) |
| **Forensic differentiation** | Brand strings: `CPPLUS`, `CP-PLUS`, `aditya infotech`, `CP-UVR`, `CP-NVR` in first 64 KB |
| **Network ports** | 37777 (same as Dahua) |
| **Accuracy in platform** | ⚠️ Moderate — brand string heuristic; Dahua pipeline is high-accuracy |

### 3.4 Honeywell Security

| Property | Detail |
|---|---|
| **Headquarters** | Charlotte, NC, USA |
| **Product lines** | Proprietary NVRs, Performance Series, MAXPRO Enterprise |
| **OEM relationships** | Modern standalone: proprietary; HRHD/HRHQ/HRHT: Dahua OEM; HRGX: Hikvision OEM (legacy) |
| **Disk filesystem** | 2-partition: Partition 1 = proprietary video storage; Partition 2 = 10 GB ext4 |
| **Superblock** | No single magic byte at sector 0; Sector 34 (offset 0x4400) contains machine data with brand strings |
| **Frame format** | Proprietary 20-byte NAL header: `frame_type (0x82/0x02) + 0x80 0x01 0x00 + width(LE) + height(LE) + nal_len(LE) + timestamp_us(LE uint64)` |
| **Video block index** | 16-byte block entries: `start_timestamp + block_number + block_group + flags` |
| **Channel delimiter** | 20 × `0x00` bytes (end-of-channel marker) |
| **MAXPRO format** | `.mpvc` / `.smpvc` (signed, Windows NTFS, SQL Server metadata) |
| **Primary codecs** | H.264, H.265 |
| **Forensic source** | Yoon & Hwang (DFRWS USA 2026, arXiv:2605.07430); GitHub `eraw1am/Honeywell-NVR-Filesystem-Tools` |
| **Accuracy in platform** | ✅ High — DFRWS 2026 peer-reviewed spec implemented |

### 3.5 TP-Link (Vigi NVR)

| Property | Detail |
|---|---|
| **Headquarters** | Shenzhen, China |
| **Product line** | Vigi NVR1004H, NVR1016H, NVR2016H, NVR4032H |
| **OEM relationship** | Not a DVR OEM; proprietary NVR hardware running embedded Linux |
| **Disk filesystem** | Proprietary circular block pool on embedded Linux; NOT DHFS |
| **Recording format** | `.dav` files containing DHAV streams (same container as Dahua) |
| **Frame format** | DHAV (FFmpeg-compatible) |
| **Forensic differentiation** | Brand strings: `TP-LINK`, `TPLINK`, `VIGI` in disk metadata |
| **Primary codecs** | H.264+, H.265, H.265+ |
| **Accuracy in platform** | ⚠️ Moderate — brand heuristic + DHAV pipeline |

### 3.6 Godrej Security Solutions

| Property | Detail |
|---|---|
| **Headquarters** | Mumbai, India |
| **Parent company** | Godrej & Boyce Mfg. Co. Ltd. |
| **OEM relationships** | **Dual-line**: STE-UR/NVR series = Dahua OEM; SeeThru Eco / ACE series = Xiongmai OEM |
| **Line A filesystem** | DHFS4.1 (Dahua) |
| **Line B filesystem** | Xiongmai raw circular blocks; sync markers: `AA 55 AA 55` or `5A A5 5A A5` |
| **Line B frame markers** | `00 00 01 FD` (I-frame), `00 00 01 FC` (P-frame) |
| **Forensic differentiation** | Brand strings: `GODREJ`, `Godrej`, `SeeThru`, `STE-UR`, `STE-NVR`, `GSS` |
| **Export formats** | Line A: `.dav`; Line B: `.264`, `.h264`, `.avi` |
| **Accuracy in platform** | ⚠️ Moderate — dual-line detection; Dahua pipeline verified |

### 3.7 Uniview (UNV)

| Property | Detail |
|---|---|
| **Headquarters** | Hangzhou, China |
| **Disk filesystem** | UBS (Universal Block Storage) — proprietary, no public spec |
| **Superblock** | No documented public magic bytes — OS reports drive as unallocated |
| **Recording format** | Raw H.265 / Ultra 265 (U-Code) NAL streams in UBS blocks |
| **Export formats** | `.mp4`, `.ts`, `.uvf` (Uniview Video File) |
| **Forensic differentiation** | Brand strings: `Uniview`, `UNV`, `Ultra265`, `UNIVIEW`, model prefixes (`NVR301`, `IPC32`) |
| **Primary codecs** | H.264, H.265/HEVC, Ultra 265 (H.265 + Uniview U-Code GOP modification) |
| **Forensic tools** | No public open-source UBS parser; commercial: Magnet DVR Examiner |
| **Accuracy in platform** | ⚠️ Low-moderate — UBS has no public spec; NAL carving best-effort |

### 3.8 Matrix Comsec (SATATYA)

| Property | Detail |
|---|---|
| **Headquarters** | Vadodara, Gujarat, India |
| **OEM relationship** | **None** — genuine indigenous Indian manufacturer (Make in India) |
| **R&D status** | DSIR-approved R&D facility; 40%+ staff in R&D |
| **Product brand** | SATATYA (NVR, HVR, SAMAS, SIGHT, CORE) |
| **Disk architecture** | Custom embedded Linux + SATATYA circular indexed block pool |
| **Native formats** | `.stm` (SATATYA Media), `.mxs` (local recording), `.avs` (backup stream) |
| **Playback** | `.stm`/`.mxs` require Matrix Device Player for decoding |
| **Export** | `.avi` (H.264, via Matrix Device Player conversion utility) |
| **Forensic differentiation** | Brand strings: `SATATYA`, `MATRIX COMSEC`, `Matrix Comsec`, `matrixcomsec.com` |
| **Network ports** | Management: 8000; HTTP: 80/8081; RTSP: 554 |
| **Primary codecs** | H.264 (Main/High), H.265/HEVC |
| **Accuracy in platform** | ⚠️ Moderate — brand + extension detection; FFmpeg multi-strategy extraction |

---

## 4. Forensic Difficulty Ranking

| Rank | Brand | Difficulty | Reason |
|---|---|---|---|
| 1 (Easiest) | **Hikvision** | Low | HIKBTREE index intact; master sector well-documented |
| 2 | **Dahua** | Low | DHFS4.1 well-documented; FFmpeg native DHAV support |
| 3 | **CP Plus** | Low | Identical to Dahua |
| 4 | **Godrej (Dahua line)** | Low | Identical to Dahua |
| 5 | **TP-Link Vigi** | Medium | DHAV compatible; no DHFS4.1 disk index |
| 6 | **Honeywell** | Medium | Proprietary NAL header spec known (DFRWS 2026) |
| 7 | **Godrej (Xiongmai line)** | High | Xiongmai block format partially reverse-engineered |
| 8 | **Matrix Comsec** | High | Proprietary .stm/.mxs; requires Matrix Device Player |
| 9 (Hardest) | **Uniview** | Very High | UBS disk format not publicly documented |

---

## 5. Deleted Video Recovery Capability

| Brand | Deletion Method | Recovery Possible | Method |
|---|---|---|---|
| Hikvision | Circular buffer overwrite | ✅ Yes (if not overwritten) | Master sector + HIKBTREE traversal for deleted blocks |
| Dahua | Circular buffer overwrite | ✅ Partial | DHAV frame carving in unallocated regions |
| Honeywell | Block pool reuse + EOC marker removal | ✅ Yes | Binary diff of block list + NAL frame carving (DFRWS 2026) |
| CP Plus / Godrej (A) | Same as Dahua | ✅ Partial | DHAV carving |
| TP-Link Vigi | File deletion on ext4 | ✅ (ext4 recovery tools) | ext4 undelete or DHAV carving |
| Matrix Comsec | SATATYA block pool reuse | ⚠️ Unknown | No published recovery methodology |
| Uniview | UBS block reuse | ⚠️ Difficult | NAL carving in unallocated UBS space |
| Godrej (Xiongmai) | Circular block overwrite | ⚠️ Difficult | XM sync marker carving |

---

## 6. Evidence Integrity Verification

All parsers in this platform compute **SHA-256 + MD5** hashes on acquisition using `backend/core/integrity/hashing.py`. Hashes are stored in the `Evidence` database table and verified before and after every parse operation. The test suite enforces that no parser modifies the evidence file's SHA-256 during `detect()` or `validate()` calls (`test_detect_and_validate_leave_sha256_unchanged`).

---

## 7. Standards & Legal Admissibility

| Standard | Applicability |
|---|---|
| **ISO/IEC 27037:2012** | Digital evidence identification, collection, acquisition, preservation |
| **NISTIR 8161r1** | CCTV digital video export profile (advocates MP4 + standardized metadata) |
| **OSAC 2022-S-0031** | Forensic digital video examination workflow |
| **SWGDE Best Practices** | Data acquisition from DVRs + H.264 analysis for examiners |
| **ASTM E3079** | Data retrieval from digital CCTV systems |

This platform complies with these standards by:
- Working only on forensic copies (never modifying originals)
- Computing cryptographic hashes at acquisition and post-parse
- Recording chain-of-custody metadata (case ID, examiner, timestamps) in the database
- Generating standardized reports with vendor attribution, confidence scores, and detection audit trails

---

*Generated by Multi-Vendor DVR/NVR Forensic Analysis Platform*
*SIH 2026 — Problem Statement SIH26150*
