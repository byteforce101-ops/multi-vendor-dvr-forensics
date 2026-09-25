# TraceX — Multi-Vendor DVR/NVR Digital Forensics Platform

[![Version](https://img.shields.io/badge/Release-v1.0.1-blue.svg)](https://github.com/byteforce101-ops/multi-vendor-dvr-forensics/releases/tag/v1.0.1)
[![Tests](https://img.shields.io/badge/Tests-191%20Passed-success.svg)](https://github.com/byteforce101-ops/multi-vendor-dvr-forensics)
[![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB.svg?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI%20%2B%20SQLAlchemy-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/Frontend-React%2018%20%2B%20Vite%20%2B%20Tailwind-61DAFB.svg?logo=react&logoColor=black)](https://vitejs.dev)
[![ONNX Runtime](https://img.shields.io/badge/AI%20Engine-ONNX%20Runtime%20%2B%20YOLOv8-FF5722.svg?logo=onnx&logoColor=white)](https://onnxruntime.ai)

TraceX is an enterprise-grade digital video evidence acquisition, frame validation, and forensic event reconstruction platform. Engineered specifically for law enforcement agencies, digital forensics laboratories, and incident response teams, TraceX automates the carving, parsing, timestamp reconstruction, and semantic tracking of proprietary DVR/NVR filesystems and raw disk images.

---

## Table of Contents
- [Key Capabilities](#-key-capabilities)
- [System Architecture](#-system-architecture)
- [Distribution & Installation](#-distribution--installation)
  - [1. Standalone Windows Executable (.exe)](#1-standalone-windows-executable-exe)
  - [2. Complete Portable Distribution (.zip)](#2-complete-portable-distribution-zip)
  - [3. Zero-Install CLI (npx)](#3-zero-install-cli-npx)
  - [4. Developer Environment Setup](#4-developer-environment-setup)
- [Command Line Interface (CLI & TUI)](#-command-line-interface-cli--tui)
- [Hardware & Parser Matrix](#-hardware--parser-matrix)
- [AI Vision & Forensic Analysis](#-ai-vision--forensic-analysis)
- [API Reference](#-api-reference)
- [Testing & Quality Assurance](#-testing--quality-assurance)
- [Contributing & License](#-contributing--license)

---

## 🌟 Key Capabilities

* **Multi-Vendor Proprietary Filesystem Decoders:** Automated sector-level parsing for Hikvision (HIKBT), Dahua/Amcrest (DHFS/DHAV), Xiongmai/JFTech (XM), CP Plus, Godrej, Honeywell, and Matrix Comsec.
* **Unallocated Space & Deleted Frame Carving:** Recovers unindexed, damaged, or deleted video frames and audio streams directly from raw physical disk dumps (`.dd`, `.raw`, `.img`, `.001`, `.dat`).
* **High-Throughput ONNX Deep Vision Engine:** Built-in ONNX Runtime execution engine delivering ~34ms/frame local inference across 80+ semantic object categories without heavy PyTorch dependencies.
* **Kinematic Trajectory & ByteTrack Tracking:** Multi-frame entity association, bounding-box tracking, velocity computation ($px/s$), and spatial occlusion handling.
* **Cryptographic Integrity & Chain of Custody:** Automated SHA-256 and MD5 hashing, presentation timestamp validation (PTS/DTS), frame-drop detection, and court-admissible dossier generation (ISO/IEC 27037 compliant).
* **TraceX AI Conversational Query Agent:** Natural language video evidence interrogation powered by Groq LLaMA models with deterministic local heuristic fallback for air-gapped forensic environments.

---

## 🏗️ System Architecture

```text
                             TRACEX APPLICATION LAYER
             ┌───────────────────────────┼───────────────────────────┐
             ▼                           ▼                           ▼
    Interactive TUI (Textual)     FastAPI Backend Engine     React Forensic Dashboard
             │                           │                           │
             └───────────────────────────┼───────────────────────────┘
                                         ▼
                     TraceX Video Analysis Service Engine
                                         │
                                         ▼
                                 TRACEX AI ENGINE
                 (Multi-Model Vision & Kinematics Orchestration)
                                         │
         ┌───────────────────────────────┼───────────────────────────────┐
         ▼                               ▼                               ▼
TraceX Deep Vision (ONNX)     TraceX Pure Forensic (HOG)     TraceX Open-Vocabulary (DINO)
         │                               │                               │
         └───────────────────────────────┼───────────────────────────────┘
                                         ▼
                               TraceX Detection Result
                                         │
         ┌───────────────────────────────┴───────────────────────────────┐
         ▼                                                               ▼
TraceX Event Builder                                           TraceX Incident Heuristics
 (Discrete Event Sequences)                                     (Kinematics & Speed Vectors)
                                         │
                                         ▼
                         Court-Admissible Forensic Dossier
```

---

## 📦 Distribution & Installation

### 1. Standalone Windows Executable (.exe)
Single portable binary. No Python, Node.js, or external drivers required.

* **Download:** [**`TraceX-DVR-Forensics.exe`** (331 MB)](https://github.com/byteforce101-ops/multi-vendor-dvr-forensics/releases/download/v1.0.1/TraceX-DVR-Forensics.exe)
* **Usage:** Open PowerShell or Command Prompt in the download directory:
  ```cmd
  TraceX-DVR-Forensics.exe --help
  ```

### 2. Complete Portable Distribution (.zip)
All-inclusive standalone package with pre-compiled web UI, batch launcher, and model weights.

* **Download:** [**`TraceX-DVR-Forensics-v1.0.1-Portable.zip`** (468 MB)](https://github.com/byteforce101-ops/multi-vendor-dvr-forensics/releases/download/v1.0.1/TraceX-DVR-Forensics-v1.0.1-Portable.zip)
* **Usage:** Extract the archive and double-click `run_tracex.bat` to launch the platform.

### 3. Zero-Install CLI (npx)
Run instantly from any terminal with Node.js installed:
```bash
npx tracex
# Or alias
npx dvrforensics
```

### 4. Developer Environment Setup

```bash
# 1. Clone the repository
git clone https://github.com/byteforce101-ops/multi-vendor-dvr-forensics.git
cd multi-vendor-dvr-forensics

# 2. Set up Python virtual environment
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# 3. Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 4. Set up Frontend (React + Vite)
cd frontend
npm install
npm run build
cd ..

# 5. Start Backend API Server
python -m uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## 💻 Command Line Interface (CLI & TUI)

TraceX includes a rich terminal interface and automated CLI tools:

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

## 🗄️ Hardware & Parser Matrix

| Vendor / Platform | Filesystem / Container | Supported Artifacts | Carving Capabilities |
| :--- | :--- | :--- | :--- |
| **Hikvision / HeimVision** | HIKBT / HIKVISION Raw | Index tables, MP4/H.264 streams | Allocated & deleted sector carving |
| **Dahua / Amcrest** | DHFS / DHAV / DAV | Segment maps, DAV chunk streams | Unindexed DAV chunk reconstruction |
| **Xiongmai (XM) / JFTech** | XM Index / Raw Streams | Multi-channel video indexes | Indexless stream recovery |
| **CP Plus** | CP Plus OEM (DHFS/XM) | Master boot records, timestamps | Video stream reassembly |
| **Godrej Security** | Godrej Enterprise DVR | Custom sector partitions | Raw block frame extraction |
| **Matrix Comsec** | Matrix Enterprise NVR | Proprietary NVR sector maps | Frame boundary carving |
| **Generic Raw Dump** | `.dd`, `.raw`, `.img`, `.001` | H.264/H.265 NAL units, MP4 headers | Byte-offset pattern scanning |

---

## 🤖 AI Vision & Forensic Analysis

TraceX integrates multi-layered computer vision for surveillance streams:

1. **Semantic Deep Vision (`backend/models/tracex_vision.onnx`):**
   * High-throughput 34ms inference with ONNX Runtime.
   * Recognizes pedestrians, vehicles (cars, motorcycles, trucks, buses), bags, backpacks, and personal items.
2. **Kinematics & Speed Vectors:**
   * Calculates instantaneous and average pixel velocities ($px/s$).
   * Identifies anomalous acceleration, sudden stops, optical looming, and close-proximity multi-object encounters.
3. **Conversational Evidence Q&A:**
   * Context-aware forensic investigation queries powered by Groq LLaMA 3.3 70B & 3.1 8B.
   * Answers questions referencing exact timestamps, track IDs, kinematic speeds, and confidence scores.

---

## 📡 API Reference

The backend exposes a comprehensive RESTful API:

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

## 🧪 Testing & Quality Assurance

TraceX maintains a rigorous automated testing pipeline covering parser boundary conditions, carving corrupt streams, and AI event summarization:

```bash
# Execute entire test suite
pytest

# Run with verbose output and coverage
pytest -v --cov=backend
```

**Test Suite Status:** `191 passed, 0 failed`

---

## ⚖️ Compliance & Standards

TraceX complies with digital forensics evidence handling standards:
* **ISO/IEC 27037:** Guidelines for identification, collection, acquisition, and preservation of digital evidence.
* **Non-Destructive Carving:** Original evidence files are strictly mounted read-only; all operations execute in isolated working copies.
* **Cryptographic Provenance:** Every carved video stream maintains immutable SHA-256 hash provenance linked to source sector offsets.

---

## 📄 License & Maintainers

Maintained and engineered by the **ByteForce Engineering Team**.  
Licensed under the [Apache License 2.0](LICENSE).
