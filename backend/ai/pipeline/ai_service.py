"""backend/ai/pipeline/ai_service.py — Compatibility module.

Re-exports TraceXAIEngine and TraceXDetectionResult from
backend.ai.pipeline.tracex_ai_engine.
"""

from __future__ import annotations

from backend.ai.pipeline.tracex_ai_engine import (
    AIDetectionResult,
    AIService,
    TraceXAIEngine,
    TraceXDetectionResult,
)

__all__ = [
    "TraceXAIEngine",
    "TraceXDetectionResult",
    "AIService",
    "AIDetectionResult",
]