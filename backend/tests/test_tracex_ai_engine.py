"""backend/tests/test_tracex_ai_engine.py — Tests for TraceX AI Engine and Rebranded Interfaces."""

import numpy as np
import pytest

from backend.ai import (
    AIDetectionResult,
    AIService,
    TraceXAIEngine,
    TraceXDetectionResult,
    TraceXForensicDetector,
    TraceXOpenVocabularyDetector,
    TraceXVisionDetector,
    TraceXOpenVocabDetector,
    build_detection_events,
    detect_incident_candidates,
)
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
from backend.video.analysis.service import TraceXVideoAnalysisService, VideoAnalysisService
from backend.video.extraction.frame_extractor import FrameSample


def test_tracex_ai_engine_aliases():
    """Verify TraceX AI Engine exports and classes."""
    assert AIService is TraceXAIEngine
    assert AIDetectionResult is TraceXDetectionResult
    assert TraceXOpenVocabularyDetector is GroundingDINODetector
    assert TraceXVideoAnalysisService is VideoAnalysisService
    assert TraceXVisionDetector is not None
    assert TraceXForensicDetector is not None
    assert TraceXOpenVocabDetector is not None


def test_tracex_ai_engine_initialization():
    """Verify TraceXAIEngine initializes properly in forensic and vision modes."""
    # Forensic mode
    engine_forensic = TraceXAIEngine(detector_engine="forensic", confidence=0.40)
    assert engine_forensic.detector_engine == "forensic"
    assert engine_forensic.forensic_detector is not None

    # Vision mode
    engine_vision = TraceXAIEngine(detector_engine="vision", confidence=0.35)
    assert engine_vision.detector_engine == "vision"


def test_tracex_ai_engine_analyze_frames():
    """Verify TraceXAIEngine processes frames and returns TraceXDetectionResult items."""
    engine = TraceXAIEngine(detector_engine="forensic", confidence=0.10)

    # Create dummy frame sequence
    frames = [
        FrameSample(
            frame_number=i,
            timestamp_seconds=float(i * 0.5),
            image=np.full((240, 320, 3), 120, dtype=np.uint8),
        )
        for i in range(3)
    ]

    results = engine.analyze_frames(frames)
    assert isinstance(results, list)
    for r in results:
        assert isinstance(r, TraceXDetectionResult)
        assert hasattr(r, "frame_number")
        assert hasattr(r, "object_type")
        assert hasattr(r, "confidence")
        assert hasattr(r, "bbox")


def test_default_vision_model_path_resolution():
    """Verify vision model path resolves without error."""
    path_str = get_default_vision_model_path()
    assert isinstance(path_str, str)
    assert len(path_str) > 0
