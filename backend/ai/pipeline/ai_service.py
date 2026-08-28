from __future__ import annotations

from dataclasses import dataclass

from backend.ai.detectors.yolo_detector import (
    YOLODetector,
)
from backend.video.extraction.frame_extractor import (
    FrameSample,
)


@dataclass
class AIDetectionResult:
    frame_number: int
    timestamp_seconds: float
    object_type: str
    confidence: float
    bbox: tuple[float, float, float, float]
    track_id: int | None


class AIService:

    def __init__(
        self,
        model_path: str = "yolo26n.pt",
        confidence: float = 0.35,
        iou: float = 0.50,
        device: str | None = None,
    ):
        self.detector = YOLODetector(
            model_path=model_path,
            confidence=confidence,
            iou=iou,
            device=device,
        )

    def analyze_frames(
        self,
        frames: list[FrameSample],
    ) -> list[AIDetectionResult]:

        results: list[AIDetectionResult] = []

        for frame in frames:

            detections = self.detector.detect(
                frame.image
            )

            for detection in detections:
                results.append(
                    AIDetectionResult(
                        frame_number=frame.frame_number,
                        timestamp_seconds=frame.timestamp_seconds,
                        object_type=detection.class_name,
                        confidence=detection.confidence,
                        bbox=detection.bbox,
                        track_id=detection.track_id,
                    )
                )

        return results