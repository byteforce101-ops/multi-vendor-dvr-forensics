# TraceX: Multi-Vendor DVR/NVR Digital Forensics Platform

[![Release](https://img.shields.io/badge/Release-v1.0.1-blue.svg)](https://github.com/byteforce101-ops/multi-vendor-dvr-forensics/releases/tag/v1.0.1)
[![Tests](https://img.shields.io/badge/Tests-191%20Passed-success.svg)](https://github.com/byteforce101-ops/multi-vendor-dvr-forensics)
[![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB.svg?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI%20%2B%20SQLAlchemy-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/Frontend-React%2018%20%2B%20Vite-61DAFB.svg?logo=react&logoColor=black)](https://vitejs.dev)
[![ONNX](https://img.shields.io/badge/Inference-ONNX%20Runtime%201.30-FF5722.svg?logo=onnx&logoColor=white)](https://onnxruntime.ai)

TraceX is a digital video forensics platform built for recovering, parsing, verifying, and analyzing surveillance recordings from proprietary DVR/NVR storage formats and raw disk images. 

Developed for digital forensics units, law enforcement laboratories, and incident response teams, TraceX provides automated unallocated space carving, timestamp reconstruction, kinematic vehicle/pedestrian tracking, and cryptographic chain-of-custody verification.

---

## Key Capabilities

* **Proprietary Filesystem Decoders:** Sector-level index parsing and stream reconstruction for Hikvision (HIKBT), Dahua/Amcrest (DHFS/DHAV), Xiongmai/JFTech (XM), CP Plus, Godrej Security, Honeywell, and Matrix Comsec.
* **Raw Disk & Deleted Frame Carving:** Recovers unindexed, damaged, or deleted video recordings directly from raw physical image dumps (`.dd`, `.raw`, `.img`, `.001`, `.dat`).
* **High-Throughput ONNX Deep Vision:** Embedded ONNX Runtime execution engine providing ~34ms/frame local inference across 80+ semantic object classes with zero external PyTorch dependency.
* **Kinematic Trajectory & ByteTrack Tracking:** Multi-frame entity association, bounding-box tracking, velocity computation ($px/s$), and spatial occlusion handling.
* **Forensic Integrity Verification:** Automated SHA-256 and MD5 hashing, presentation timestamp validation (PTS/DTS), frame-drop detection, and ISO/IEC 27037-compliant forensic dossier export.
* **Forensic AI Query Interface:** Context-aware natural language evidence queries powered by Groq LLaMA models, with deterministic local heuristic fallback for air-gapped forensic laboratories.

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

## Distribution and Installation

### 1. Standalone Windows Executable (.exe)
Single portable binary. No Python, Node.js, or external drivers required.

* **Download:** [`TraceX-DVR-Forensics.exe` (331 MB)](https://github.com/byteforce101-ops/multi-vendor-dvr-forensics/releases/download/v1.0.1/TraceX-DVR-Forensics.exe)
* **Usage:** Open PowerShell or Command Prompt in the download directory:
  ```cmd
  TraceX-DVR-Forensics.exe --help
  ```

### 2. Complete Portable Distribution (.zip)
All-inclusive standalone package with pre-compiled web UI, batch launcher, and model weights.

* **Download:** [`TraceX-DVR-Forensics-v1.0.1-Portable.zip` (468 MB)](https://github.com/byteforce101-ops/multi-vendor-dvr-forensics/releases/download/v1.0.1/TraceX-DVR-Forensics-v1.0.1-Portable.zip)
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

## Supported Hardware & Filesystem Formats

| Vendor / Platform | Filesystem / Container | Supported Artifacts | Carving Capabilities |
| :--- | :--- | :--- | :--- |
| **Hikvision / HeimVision** | HIKBT / HIKVISION Raw | Index tables, MP4/H.264 streams | Allocated and unallocated sector carving |
| **Dahua / Amcrest** | DHFS / DHAV / DAV | Segment maps, DAV chunk streams | Unindexed DAV chunk reconstruction |
| **Xiongmai (XM) / JFTech** | XM Index / Raw Streams | Multi-channel video indexes | Indexless stream recovery |
| **CP Plus** | CP Plus OEM (DHFS/XM) | Master boot records, timestamps | Video stream reassembly |
| **Godrej Security** | Godrej Enterprise DVR | Custom sector partitions | Raw block frame extraction |
| **Matrix Comsec** | Matrix Enterprise NVR | Proprietary NVR sector maps | Frame boundary carving |
| **Generic Raw Image** | `.dd`, `.raw`, `.img`, `.001` | H.264/H.265 NAL units, MP4 headers | Byte-offset pattern scanning |

---

## AI Vision and Kinematics Engine

TraceX incorporates a layered computer vision pipeline optimized for surveillance footage:

1. **Semantic Vision Detector (`backend/models/tracex_vision.onnx`):**
   * High-throughput 34ms inference with ONNX Runtime.
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

TraceX maintains an automated test suite covering parser boundary conditions, corrupt stream carving, and AI event summarization:

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
* **Cryptographic Provenance:** Every carved video stream maintains immutable SHA-256 hash verification linked to source sector offsets.

---

## License

TraceX Digital Forensics Platform is maintained by the ByteForce Engineering Team.  
Distributed under the [Apache License 2.0](LICENSE).
