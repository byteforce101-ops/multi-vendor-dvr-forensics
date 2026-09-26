# TraceX: Multi-Vendor DVR/NVR Digital Forensics Platform

[![Release](https://img.shields.io/badge/Release-v1.0.1-blue.svg)](https://github.com/byteforce101-ops/multi-vendor-dvr-forensics/releases/tag/v1.0.1)
[![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB.svg?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI%20%2B%20SQLAlchemy-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/Frontend-React%2018%20%2B%20Vite-61DAFB.svg?logo=react&logoColor=black)](https://vitejs.dev)
[![ONNX](https://img.shields.io/badge/Inference-ONNX%20Runtime%201.30-FF5722.svg?logo=onnx&logoColor=white)](https://onnxruntime.ai)

TraceX is an enterprise-grade digital video forensics and incident reconstruction platform designed for recovering, parsing, verifying, and analyzing surveillance recordings from proprietary DVR/NVR storage formats, raw disk images, and unallocated sector dumps.

Developed for digital forensics laboratories (DFIR), law enforcement agencies, and security audit teams, TraceX provides automated multi-vendor superblock parsing, unallocated space stream carving, kinematic speed/trajectory tracking, forensic timestamp reconstruction, and cryptographic chain-of-custody verification.

---
##  Test Data & Vendor Sample Evidence

Sample raw DVR disk images, stream recordings, and test datasets across supported vendor formats (Hikvision, Dahua, CP Plus, etc.) are available for testing:

*  **Multi-Vendor DVR Test Files:**
*   [Google Drive - Multi-Vendor DVR Test Datasets](https://drive.google.com/drive/folders/1s9Ourdm1UIjgbhcknEoxrjAg0eouQfJS?usp=sharing)
*  [Google Drive - Supplementary Test Repository](https://drive.google.com/drive/folders/1yTL6SCxSwxwO3HGjoc3bi_5NoPK8LCiR?usp=drive_link)

  
## Key Capabilities

* **11 Multi-Vendor DVR/NVR Parsers:** Native sector-level filesystem parsing and container reconstruction for Hikvision, Dahua, Honeywell, Matrix Comsec, TP-Link VIGI, Godrej Security, HeimVision, Uniview (UNV), CP Plus, Generic Forensic Carver, and Standard Video Containers.
* **Unallocated Space & Deleted Stream Carving:** Recovers damaged, wiped, or orphaned video recordings directly from raw physical disk dumps (`.dd`, `.raw`, `.img`, `.001`, `.bin`, `.dat`).
* **High-Throughput Local Vision Inference:** Embedded ONNX Runtime execution engine (~34ms/frame) detecting vehicles, pedestrians, and scene entities with zero external PyTorch dependencies.
* **Kinematic Trajectory & Speed Estimation:** Multi-frame tracking via ByteTrack, bounding-box motion vectors, instantaneous velocity computation ($px/s$), acceleration anomalies, and spatial collision analysis.
* **Forensic Timestamp & Stream Verification:** Automated SHA-256/MD5 hashing, Presentation Timestamp (PTS/DTS) validation, frame-drop detection, and ISO/IEC 27037-compliant dossier generation.
* **Conversational Forensic AI Investigator:** Natural language evidence querying powered by Groq LLaMA models, with deterministic local heuristics for air-gapped forensic environments.
* **Synthetic Evidence Generation Tooling:** Built-in toolchain (`scripts/generate_all_vendor_samples.py`) to transcode and encapsulate any standard video into authentic vendor filesystem disk images and containers for simulation, validation, and training.

---

## Supported Hardware & Vendor Parsers

TraceX includes dedicated decoders for major global and Indian surveillance manufacturers:

| Vendor / Platform | Filesystem / Container | File Signatures & Markers | Forensic Extraction Capabilities |
| :--- | :--- | :--- | :--- |
| **Hikvision** | `HIKBT` / Raw Disk (`.dd`, `.img`) | `HIKVISION@HANGZHOU`, `HIKBTREE`, `HIK.2011.03.08` | Master Block parsing, B-tree index traversal, MPEG-PS data block carving |
| **Dahua / Amcrest** | `DHFS4.1` / DHAV (`.dav`, `.dd`) | `DHFS4.1`, `DHAV`, `DAHUA`, `dhav` footers | Superblock decoding, frame-level timestamp extraction, multi-channel demuxing |
| **Honeywell Security** | Proprietary FS / MAXPRO (`.dd`, `.mpvc`) | Sector 34 (`0x4400`) brand strings, 20-byte NAL headers (`0x82800100` / `0x02800100`) | Proprietary sector parsing, NAL unit reconstruction, MAXPRO export decoding |
| **Matrix Comsec** | SATATYA Native (`.stm`, `.mxs`, `.avs`) | `MATRIX COMSEC`, `SATATYA NVR`, NAL Annex B start codes | Indigenous Indian NVR stream container parsing, raw H.264/H.265 extraction |
| **TP-Link VIGI** | VIGI NVR (`.dav`, `.raw`, `.dd`) | `TP-LINK`, `VIGI`, `NVR1004H`, DHAV container framing | VIGI partition carving, DHAV stream demuxing |
| **Godrej Security** | GSS SeeThru / STE-NVR (`.bin`, `.dd`) | `GODREJ SECURITY`, `SeeThru`, Xiongmai `AA55AA55` sync tags | Line A (Dahua OEM) & Line B (Xiongmai `000001FD`/`FC` stream carving) |
| **HeimVision** | Raw HEVC Stream (`.dat`, `.raw`) | H.265 VPS markers (`0000000140`), SPS/PPS/IDR NALs | Elementary HEVC stream extraction and lossless MP4 remuxing |
| **Uniview (UNV)** | Universal Block Storage (`.uvf`, `.dd`) | `UNIVIEW`, `UNV`, `Ultra265`, `NVR301`, IDR NAL codes | UBS block scanning, Ultra265/H.264 segment boundary carving |
| **CP Plus** | CP-UVR / CP-NVR (`.dav`, `.dd`) | `CPPLUS`, `CP-UVR`, `Aditya Infotech` metadata | Dahua OEM chain-of-custody attribution, DHAV frame reassembly |
| **Forensic Disk Carver** | Raw Unallocated (`.dd`, `.raw`, `.img`) | MPEG-PS packs (`000001BA`), MP4 boxes (`ftyp`), FLV, AVI, MKV | Headerless multi-stream carving from corrupted or wiped physical drives |
| **Generic Video** | Standard Containers (`.mp4`, `.avi`, `.mkv`) | ISO Media, RIFF AVI, Matroska headers | Container metadata extraction and direct analytical ingestion |

---

## System Architecture

```text
                             TRACEX APPLICATION LAYER
             +---------------------------+---------------------------+
             |                           |                           |
    Interactive TUI (Textual)     FastAPI REST API           React Web Dashboard
             |                           |                           |
             +---------------------------+---------------------------+
                                         |
                                         v
                     TraceX Video Analysis Service Engine
                                         |
                                         v
                                 TRACEX AI ENGINE
                 (Multi-Model Vision & Kinematics Orchestration)
                                         |
         +-------------------------------+-------------------------------+
         |                               |                               |
TraceX Deep Vision (ONNX)     TraceX Pure Forensic (HOG)     TraceX Open-Vocabulary (DINO)
         |                               |                               |
         +-------------------------------+-------------------------------+
                                         |
                                         v
                               TraceX Detection Result
                                         |
         +-------------------------------+-------------------------------+
         |                                                               |
TraceX Event Builder                                           TraceX Incident Heuristics
 (Discrete Event Sequences)                                     (Kinematics & Speed Vectors)
                                         |
                                         v
                         Court-Admissible Forensic Dossier
```

---

## Installation and Quick Start

### 1. Standalone Windows Executable (.exe)
Single portable binary. No Python, Node.js, or external drivers required.

* **Download:** [`TraceX-DVR-Forensics.exe` (331 MB)](https://github.com/byteforce101-ops/multi-vendor-dvr-forensics/releases/download/v1.0.1/TraceX-DVR-Forensics.exe)
* **Usage:** Open PowerShell or Command Prompt in the download directory:
  ```cmd
  TraceX-DVR-Forensics.exe --help
  ```

### 2. Complete Portable Distribution (.zip)
All-inclusive standalone package with pre-compiled web UI, batch launcher, and model weights.

* **Download:** [`TraceX-DVR-Forensics-Portable.zip` (468 MB)](https://github.com/byteforce101-ops/multi-vendor-dvr-forensics/releases/download/v1.0.1/TraceX-DVR-Forensics-Portable.zip)
* **Usage:** Extract the archive and execute `run_tracex.bat` to launch the platform.

### 3. Zero-Install CLI (npx)
Run directly in any terminal with Node.js:
```bash
npx tracex
```

### 4. Developer Environment Setup

```bash
# Clone the repository
git clone https://github.com/byteforce101-ops/multi-vendor-dvr-forensics.git
cd multi-vendor-dvr-forensics

# Set up Python virtual environment
python -m venv .venv

# Activate environment (Windows)
.venv\Scripts\activate
# Activate environment (Linux/macOS)
source .venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Build Frontend (React + Vite)
cd frontend
npm install
npm run build
cd ..

# Launch Backend API Server
python -m uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## Command Line Interface (CLI & TUI)

TraceX provides a full-featured terminal interface and individual CLI subcommands:

```bash
# Launch interactive full-screen Terminal User Interface (TUI)
tracex tui

# Run guided analysis wizard (detect -> parse -> extract -> analyze)
tracex --file evidence.dd --pipeline

# Detect proprietary DVR filesystem format
tracex detect path/to/evidence.dd

# Parse disk structure and list recordings
tracex parse path/to/evidence.dd --output-dir ./extracted

# Extract and carve video streams
tracex extract path/to/evidence.dd --output-dir ./extracted

# Run deep AI video analysis on an extracted video
tracex analyze path/to/video.mp4 --confidence 0.35

# Search timeline events using natural language
tracex search --case CASE_001 --query "red vehicle moving above average speed"

# Apply surveillance enhancement filters (CLAHE, gamma adjustment)
tracex enhance path/to/low_light.mp4 --output enhanced.mp4
```

---

## Synthetic Evidence Generation

TraceX includes an evidence generation utility to transform any standard video (e.g. CCTV, dashcam, MP4) into authentic disk images and stream files for all 11 parsers:

```bash
# Generate evidence packages for all 11 parsers from an input video
python scripts/generate_all_vendor_samples.py "C:\path\to\video.mp4" -o "output\vendor_samples"

# Specify a custom topic prefix for filenames
python scripts/generate_all_vendor_samples.py "C:\path\to\video.mp4" -o "output\vendor_samples" --prefix incident_01
```

Generated packages:
* `hikvision_*.dd` — Master Block + HIKBTREE index + MPEG-PS data block
* `dahua_*.dav` & `dahua_*.dd` — DHAV stream & DHFS4.1 disk image
* `honeywell_*.dd` — Sector 34 machine data + 20-byte NAL headers
* `matrix_satatya_*.stm` — SATATYA Media stream container
* `tplink_vigi_*.dav` — VIGI metadata + DHAV frame stream
* `godrej_seethru_*.bin` — Xiongmai `AA55AA55` sync tags + NAL stream
* `heimvision_*.dat` — Raw HEVC/H.265 elementary stream
* `uniview_*.uvf` — Ultra265 Video Export container
* `cpplus_*.dav` — CP-UVR Aditya Infotech metadata + DHAV stream
* `carver_raw_disk_*.dd` — Unallocated physical disk with MPEG-PS packs
* `generic_*.mp4` — Standard MP4 video container

---

## AI Vision and Kinematics Engine

TraceX incorporates a layered computer vision pipeline optimized for surveillance footage:

1. **Semantic Vision Detector (`backend/models/tracex_vision.onnx`):**
   * High-throughput ~34ms inference with ONNX Runtime.
   * Classifies pedestrians, vehicles (cars, motorcycles, trucks, buses), bags, backpacks, and personal accessories.
2. **Kinematics & Speed Estimation:**
   * Computes instantaneous and average pixel velocities ($px/s$).
   * Flags anomalous acceleration, rapid deceleration, optical looming, and close-proximity multi-object encounters.
3. **Conversational Evidence Q&A:**
   * Context-aware investigative queries powered by Groq LLaMA models.
   * Formulates forensic findings citing exact timestamps, track IDs, kinematic speeds, and confidence metrics.

---

## REST API Reference

The backend exposes a structured RESTful API for integration into laboratory pipelines:

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/health` | Service health and operational status |
| `GET` | `/overview/stats` | Aggregated forensic workspace statistics |
| `POST` | `/video/analyze` | Ingest and analyze DVR disk image or video stream |
| `POST` | `/video/query` | Natural language video Q&A with forensic LLM agent |
| `GET` | `/video/{id}/stream` | Stream normalized MP4 video for evidence preview |
| `GET` | `/cases` | List, filter, and inspect forensic cases |
| `POST` | `/cases` | Create new investigative case container |
| `GET` | `/download/desktop-exe` | Download standalone Windows executable |
| `GET` | `/download/portable-zip` | Download complete portable archive package |

Interactive Swagger documentation is available at `http://localhost:8000/docs`.

---

## Automated Test Suite

TraceX maintains an automated test suite covering parser contract invariants, corrupt stream carving, database migrations, and AI event summarization:

```bash
# Run test suite
pytest

# Run with verbose output and coverage report
pytest -v --cov=backend
```

**Test Suite Status:** `191 passed, 0 failed`

---

## Standards and Evidence Handling

TraceX is designed around digital forensics evidence preservation principles:
* **ISO/IEC 27037 Compliance:** Adheres to standards for the identification, collection, acquisition, and preservation of digital evidence.
* **Non-Destructive Processing:** Original evidence files are opened in read-only mode; all carving and normalization occurs in isolated working directories.
* **Cryptographic Provenance:** Every carved video stream maintains immutable SHA-256 and MD5 hash verification linked to source sector offsets.

---

## License

TraceX Digital Forensics Platform is maintained by the ByteForce Engineering Team.  

