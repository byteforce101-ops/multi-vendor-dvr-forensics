"""TraceX AI Detectors Package.

Contains forensic computer vision and deep learning detectors:
- TraceXForensicDetector: Pure forensic HOG/Haar/MOG2 detector.
- TraceXVisionDetector: High-speed semantic vision detector.
- TraceXOpenVocabularyDetector (GroundingDINODetector): Zero-shot open-vocabulary detector.
- TraceXOpenVocabDetector: Dynamic open-vocabulary vision detector.
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

TraceXOpenVocabularyDetector = GroundingDINODetector

__all__ = [
    # TraceX Branded
    "TraceXForensicDetector",
    "TraceXForensicDetection",
    "TraceXVisionDetector",
    "TraceXVisionDetection",
    "TraceXOpenVocabularyDetector",
    "TraceXOpenVocabDetector",
    "TraceXOpenVocabDetection",
    "get_default_vision_model_path",
    "GroundingDINODetector",
]
