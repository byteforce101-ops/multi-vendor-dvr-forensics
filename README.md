# TraceX — DVR Forensics Platform

TraceX is an end-to-end digital video forensics platform designed for recovering, parsing, analyzing, and reconstructing surveillance recordings from proprietary DVR filesystem formats and video streams.

TraceX features a dedicated **TraceX AI Engine** that orchestrates multi-model computer vision, forensic motion heuristics, kinematic event reconstruction, and conversational evidence Q&A.

---

## Architecture Overview

```
                            TRACEX APPLICATION LAYER
                       (CLI / TUI / REST API / Frontend)
                                       │
                                       ▼
                   TraceX Video Analysis Service Engine
                 (backend.video.analysis.service.VideoAnalysisService)
                                       │
                                       ▼
                              TRACEX AI ENGINE
                 (backend.ai.pipeline.tracex_ai_engine.TraceXAIEngine)
                                       │
         ┌─────────────────────────────┼─────────────────────────────┐
         ▼                             ▼                             ▼
TraceX Deep Vision             TraceX Pure Forensic         TraceX Open Vocabulary
    Detector                        Detector                       Detector
(TraceXVisionDetector)       (TraceXForensicDetector)     (TraceXOpenVocabularyDetector)
         │                             │                             │
         └─────────────────────────────┼─────────────────────────────┘
                                       ▼
                             TraceX Detection Result
                            (TraceXDetectionResult)
                                       │
         ┌─────────────────────────────┴─────────────────────────────┐
         ▼                                                           ▼
TraceX Event Builder                                      TraceX Incident Heuristics
 (build_detection_events)                                  (detect_incident_candidates)
                                       │
                                       ▼
                     TraceX Forensic Intelligence Summary
```

---

## TraceX AI Engine Subsystem

TraceX integrates a layered AI detection and analysis architecture:

1. **TraceX AI Engine (`TraceXAIEngine`)**:
   - Central application-level intelligence orchestrator located at `backend.ai.pipeline.tracex_ai_engine`.
   - Coordinates video frame preprocessing, motion-guided ROI extraction, multi-model object detection, and cross-frame track association.

2. **Detection Engines**:
   - **TraceX Pure Forensic Detector (`TraceXForensicDetector`)**: 100% local, weightless pedestrian HOG, Haar body cascades, and MOG2 background morphometrics for rapid CPU-only forensic triage.
   - **TraceX Deep Vision Detector (`TraceXVisionDetector`)**: High-speed semantic object detection and persistent multi-frame tracking.
   - **TraceX Open-Vocabulary Detector (`TraceXOpenVocabularyDetector` / `GroundingDINODetector`)**: Transformer-based zero-shot discovery for domain-specific or uncommon forensic entities.

3. **Forensic Intelligence & Event Reconstruction**:
   - **TraceX Event Builder (`build_detection_events`)**: Aggregates per-frame bounding box detections into discrete spatio-temporal event sequences.
   - **TraceX Incident Heuristics (`detect_incident_candidates`)**: Rule-based physics and kinematic heuristics detecting multi-vehicle proximity, collisions, optical looming, and sudden decelerations.
   - **TraceX Forensic Intelligence Summary (`build_forensic_summary`)**: Generates structured investigative headlines, activity chronologies, and confidence ratings.

---

## Quick Start & Usage

### Running the TraceX CLI / TUI

Launch the full-screen interactive Terminal User Interface (TUI):
```bash
# Windows batch launcher
.\tracex.bat

# Python direct
python -m backend.cli.main
```

Analyze a specific video or evidence file directly:
```bash
python -m backend.cli.main --file path/to/evidence.dd
```

Run automated CLI video analysis:
```bash
python -m backend.cli.main analyze path/to/video.mp4
```

### Running the Backend API Server

Start the FastAPI backend server:
```bash
python run_backend.py
```

### Running Tests

Execute the full automated test suite:
```bash
pytest
```
