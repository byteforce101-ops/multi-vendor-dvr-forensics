"""TraceX AI Events Package.

Contains forensic event building and incident heuristics:
- build_detection_events: Groups frame-level detections into spatio-temporal events.
- detect_incident_candidates: Identifies proximity, collision, looming, and deceleration candidates.
- detect_proximity_events: Multi-vehicle proximity and contact detection.
- detect_ego_collision_events: Dashcam / ego-vehicle crash candidate detection.
- detect_sudden_stop_events: Sudden deceleration / stop upon impact detection.
- build_disappearance_events: Detects object disappearance candidate events.
"""

from __future__ import annotations

from backend.ai.events.disappearance_detector import build_disappearance_events
from backend.ai.events.event_builder import build_detection_events
from backend.ai.events.incident_heuristics import (
    detect_ego_collision_events,
    detect_incident_candidates,
    detect_proximity_events,
    detect_sudden_stop_events,
)

__all__ = [
    "build_detection_events",
    "detect_incident_candidates",
    "detect_proximity_events",
    "detect_ego_collision_events",
    "detect_sudden_stop_events",
    "build_disappearance_events",
]
