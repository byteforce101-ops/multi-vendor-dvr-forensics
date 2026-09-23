# System Architecture Documentation
## Multi-Vendor DVR/NVR Forensic Analysis Platform

---

## 1. System Overview

The platform is a **modular, API-first forensic analysis system** for standardized acquisition, parsing, recovery, analysis, and reporting of CCTV/DVR/NVR surveillance evidence. It supports **8 major DVR/NVR brands** (Dahua, Hikvision, CP Plus, Honeywell, TP-Link, Godrej, Uniview, Matrix Comsec) with a unified forensic workflow that reduces dependency on vendor-specific tools.

---

## 2. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        PRESENTATION LAYER                                    │
│  ┌──────────────────┐  ┌──────────────────┐  ┌────────────────────────────┐ │
│  │   React Frontend  │  │    CLI (Rich TUI) │  │  REST API (FastAPI/OpenAPI)│ │
│  │  (Next.js / Vercel│  │  dvr-forensics   │  │  /api/cases, /api/evidence │ │
│  └─────────┬────────┘  └────────┬──────────┘  └───────────┬──────────────┘ │
└────────────┼────────────────────┼───────────────────────────┼───────────────┘
             │                    │                           │
┌────────────┼────────────────────┼───────────────────────────┼───────────────┐
│            ▼                    ▼                           ▼                │
│                          CORE SERVICES LAYER                                 │
│  ┌───────────────────┐  ┌────────────────────┐  ┌──────────────────────────┐│
│  │ Acquisition Svc   │  │  Parser Manager    │  │   AI Analysis Engine     ││
│  │ (hashing, verify) │  │  (detect_candidates│  │  (TraceX: HOG + motion   ││
│  │ integrity: SHA256 │  │   parse, extract)  │  │   detection, loitering)  ││
│  │ + MD5             │  │                    │  │                          ││
│  └───────────────────┘  └────────┬───────────┘  └──────────────────────────┘│
└─────────────────────────────────┼────────────────────────────────────────────┘
                                  │
┌─────────────────────────────────┼────────────────────────────────────────────┐
│                        PARSER LAYER                                           │
│  ┌─────────┐ ┌──────┐ ┌──────────┐ ┌──────┐ ┌──────────┐ ┌──────┐          │
│  │Hikvision│ │Dahua │ │Honeywell │ │Matrix│ │TP-Link   │ │Godrej│          │
│  │ 0.90    │ │ 0.90 │ │   0.85   │ │ 0.82 │ │  0.80    │ │ 0.80 │          │
│  └─────────┘ └──────┘ └──────────┘ └──────┘ └──────────┘ └──────┘          │
│  ┌──────────┐ ┌──────┐ ┌──────────────────┐ ┌─────────────────────┐        │
│  │HeimVision│ │Univew│ │CP Plus    0.72   │ │ForensicDiskCarver   │        │
│  │  0.75    │ │ 0.75 │ │                  │ │        0.65         │        │
│  └──────────┘ └──────┘ └──────────────────┘ └─────────────────────┘        │
│                                                                               │
│  BaseDVRParser ABC: detect() → validate() → parse() → extract_recordings()  │
└───────────────────────────────────────────────────────────────────────────────┘
                                  │
┌─────────────────────────────────┼────────────────────────────────────────────┐
│                        DATA LAYER                                             │
│  ┌──────────────────────────────────────────────────────────────────────────┐│
│  │  PostgreSQL (production via Render) / SQLite (local dev/test)            ││
│  │  Alembic migrations                                                      ││
│  │  Tables: Case, Evidence, Event, NormalizedRecording                      ││
│  │  Evidence columns: detection_confidence, detection_info (JSON)           ││
│  └──────────────────────────────────────────────────────────────────────────┘│
└───────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Component Descriptions

### 3.1 Parser Layer (`backend/parsers/`)

The core forensic engine. Each parser implements `BaseDVRParser` ABC:

| Method | Signature | Purpose |
|---|---|---|
| `detect()` | `(path) → (bool, float, dict)` | Identify vendor from binary signatures. **Must never raise on any input.** |
| `validate()` | `(path) → (bool, list[str])` | Structural validation; returns warnings (not hard failures) |
| `parse()` | `(path, out_dir) → ParseResult` | Enumerate NormalizedRecording objects without modifying evidence |
| `extract_recordings()` | `(path, out_dir, recordings, master_block) → ParseResult` | Extract/remux video to standard MP4 via FFmpeg |

**Parser Manager** (`backend/parsers/registry.py`) runs `detect_candidates()` which:
1. Tries all parsers in confidence order
2. Short-circuits once a parser exceeds `max_confidence` threshold (avoids redundant calls)
3. Records full audit trail of all candidate scores for reporting

### 3.2 Acquisition & Integrity (`backend/core/acquisition/`, `backend/core/integrity/`)

- `compute_hashes(path)` → `{"sha256": ..., "md5": ...}` computed in 8 KB chunks
- `verify_hash(path, expected_sha256)` → bool
- All evidence is hashed on ingest; hash verified before and after every parse
- Results stored in `Evidence.detection_confidence` + `Evidence.detection_info`

### 3.3 REST API (`backend/api/main.py`)

FastAPI application with OpenAPI docs at `/docs`:

| Endpoint | Method | Description |
|---|---|---|
| `/api/cases` | GET/POST | Create and list forensic cases |
| `/api/cases/{id}/evidence` | GET/POST | Add evidence to a case |
| `/api/evidence/{id}/parse` | POST | Parse evidence (auto-detects vendor) |
| `/api/evidence/{id}/extract` | POST | Extract recordings to output dir |
| `/api/evidence/{id}/analyze` | POST | Run AI motion/entity detection |
| `/api/evidence/{id}/report` | GET | Generate forensic report |
| `/api/search` | POST | Semantic search across events |

### 3.4 CLI (`backend/cli/`)

Rich terminal UI with commands:
- `dvr-forensics detect <path>` — detect vendor, show candidate table + hex dump + ASCII strings
- `dvr-forensics parse <path>` — parse recordings with detection confidence
- `dvr-forensics extract <path>` — extract to MP4
- `dvr-forensics analyze <path>` — AI event detection
- `dvr-forensics case <subcommand>` — case management

### 3.5 AI Analysis Engine (`backend/ai/`)

- **TraceX Forensic Vision**: HOG-based human detection + morphometric analysis
- **Entity Tracker**: assigns track IDs, computes trajectories, detects loitering
- **Event Builder**: reconstructs higher-level forensic events from raw detections
- **Forensic Report Renderer**: generates formatted evidence summaries

### 3.6 Database (`backend/db/`)

SQLAlchemy models with Alembic migrations:

```
Case ──< Evidence ──< Event
              │
              └── detection_confidence: Float
              └── detection_info: JSON (full candidate audit trail)
              └── sha256_hash: String
              └── vendor: String
              └── parser_version: String
```

---

## 4. Forensic Workflow (Standard Operating Procedure)

```
1. ACQUISITION
   ├── Create case (POST /api/cases)
   ├── Add evidence file (POST /api/cases/{id}/evidence)
   └── SHA-256 + MD5 computed and stored on ingest

2. DETECTION
   ├── detect_candidates() runs all 11 parsers in confidence order
   ├── Short-circuit on high-confidence match (≥ max_confidence)
   └── Full candidate audit trail stored in Evidence.detection_info

3. VALIDATION
   └── validate() confirms structural integrity, returns warnings

4. PARSING
   ├── parse() enumerates NormalizedRecording objects
   ├── Channel IDs, timestamps, resolution, codec metadata extracted
   └── Evidence SHA-256 re-verified (must not change)

5. EXTRACTION
   ├── extract_recordings() remuxes to standard MP4 via FFmpeg
   ├── Extraction outputs stored in case output directory
   └── Extracted file paths stored in NormalizedRecording.extracted_path

6. ANALYSIS (optional)
   └── AI motion/entity detection on extracted MP4

7. REPORTING
   └── Forensic report with: vendor, confidence, hash, recordings, warnings, timestamps
```

---

## 5. Deployment Architecture

```
Production:
  Frontend  → Vercel (Next.js)
  Backend   → Render (FastAPI + Uvicorn)
  Database  → Render PostgreSQL

Local Development:
  Backend   → uvicorn backend.api.main:app --reload
  Database  → SQLite (auto-created at backend/db/forensics.db)
  Tests     → pytest with isolated per-test SQLite (temp file, never the real DB)
```

---

## 6. Security & Evidence Integrity Controls

| Control | Implementation |
|---|---|
| Read-only evidence access | `mmap.ACCESS_READ` in all binary parsers |
| Hash verification before/after | `verify_hash()` in parse pipeline |
| Isolated test database | `pytest_configure` hook pins to temp SQLite before any import |
| Output directory sandboxing | Tests verify extracted files stay within `output_dir` |
| No parser can raise on bad input | `TestParserContract` enforces: all 11 parsers must return `(False, 0.0, {})` on empty/random/truncated inputs |
| Vendor accuracy transparency | `detection_confidence` + `detection_info` stored per evidence item |

---

## 7. Key Dependencies

| Package | Purpose |
|---|---|
| `fastapi` | REST API framework |
| `sqlalchemy` + `alembic` | ORM + migrations |
| `ffmpeg` (system) | Video remuxing and demuxing |
| `ffprobe` (system) | Video metadata extraction |
| `rich` | CLI terminal UI |
| `pytest` | Test suite |
| `mmap` (stdlib) | Read-only memory-mapped file access for binary parsing |
| `struct` (stdlib) | Binary struct decoding for proprietary frame formats |

---

*Multi-Vendor DVR/NVR Forensic Analysis Platform*
*SIH 2026 — Problem Statement SIH26150*
