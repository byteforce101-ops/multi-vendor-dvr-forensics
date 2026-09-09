"""TraceX AI & Detection Engine Package.

Provides the complete TraceX forensic intelligence and object detection pipeline:
- TraceXAIEngine: Unified multi-model detection and tracking engine.
- TraceXDetectionResult: Forensic per-frame object detection model.
- TraceXForensicDetector: Pure CPU-based forensic detector & tracker.
- TraceXVisionDetector: Deep vision semantic detector & tracker.
- TraceXOpenVocabularyDetector: Open-vocabulary discovery detector.
- TraceXOpenVocabDetector: Dynamic open-vocabulary detector.
- Event builders and incident candidate heuristics.
"""

from __future__ import annotations

from backend.ai.detectors.grounding_dino_detector import GroundingDINODetector
from backend.ai.detectors.tracex_forensic_detector import (
    TraceXForensicDetection,
    TraceXForensicDetector,
)
from backend.ai.detectors.tracex_vision_detector import (
    TraceXVisionDetection,
    TraceXVisionDetector,
    get_default_vision_model_path,
)
from backend.ai.detectors.tracex_open_vocab_detector import (
    TraceXOpenVocabDetection,
    TraceXOpenVocabDetector,
)
from backend.ai.events.disappearance_detector import build_disappearance_events
from backend.ai.events.event_builder import build_detection_events
from backend.ai.events.incident_heuristics import (
    detect_ego_collision_events,
    detect_incident_candidates,
    detect_proximity_events,
    detect_sudden_stop_events,
)
from backend.ai.pipeline.tracex_ai_engine import (
    AIDetectionResult,
    AIService,
    TraceXAIEngine,
    TraceXDetectionResult,
)

TraceXOpenVocabularyDetector = GroundingDINODetector

__all__ = [
    # Top-level TraceX AI Engine
    "TraceXAIEngine",
    "TraceXDetectionResult",
    # Legacy aliases
    "AIService",
    "AIDetectionResult",
    # TraceX Detectors
    "TraceXForensicDetector",
    "TraceXForensicDetection",
    "TraceXVisionDetector",
    "TraceXVisionDetection",
    "TraceXOpenVocabularyDetector",
    "TraceXOpenVocabDetector",
    "TraceXOpenVocabDetection",
    "get_default_vision_model_path",
    "GroundingDINODetector",
    # Forensic Event Heuristics
    "build_detection_events",
    "detect_incident_candidates",
    "detect_proximity_events",
    "detect_ego_collision_events",
    "detect_sudden_stop_events",
    "build_disappearance_events",
]
