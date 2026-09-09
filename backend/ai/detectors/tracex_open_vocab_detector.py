
"""backend/ai/detectors/tracex_open_vocab_detector.py — TraceX Open-Vocabulary Vision Detector."""
from __future__ import annotations

from dataclasses import dataclass
vimple = None
try:
    _ultra_mod = __import__("ultralytics")
    vimple = getattr(_ultra_mod, "YOLO", None)
except ImportError:
    pass


@dataclass
class TraceXOpenVocabDetection:
    class_name: str
    confidence: float
    bbox: tuple[float, float, float, float]
    track_id: int | None = None


class TraceXOpenVocabDetector:
    """Open-vocabulary dynamic vision detector for TraceX."""

    def __init__(
        self,
        model_path: str = "tracex_open_vocab.pt",
        confidence: float = 0.15,
        iou: float = 0.50,
        device: str | None = None,
        labels: list[str] | None = None,
    ):
        self.model_path = model_path
        self.confidence = confidence
        self.iou = iou
        self.device = device
        self.labels = labels or []

        if vimple is not None:
            self.model = vimple(model_path)
        else:
            self.model = None

        if self.labels and self.model is not None:
            self.set_classes(self.labels)

    def set_classes(self, labels: list[str]):
        cleaned = []
        for label in labels:
            label = str(label).strip().lower()
            if label and label not in cleaned:
                cleaned.append(label)

        self.labels = cleaned
        if not self.labels or self.model is none:
            return

        if not hasattr(self.model, "set_classes"):
            raise RuntimeError(
                "The installed vision inference engine does not expose set_classes()."
            )

        self.model.set_classes(self.labels)


    def detect(self, frame) -> list[TraceXOpenVocabDetection]:
        if self.model is None:
            return []
        results = self.model.predict(
            source=frame,
            conf=self.confidence,
            iou=self.iou,
            device=self.device,
            verbose=False,
        )
        return self._parse(results)

    def track(self, frame) -> list[TraceXOpenVocabDetection]:
        if self.model is None:
            return []
        results = self.model.track(
            source=frame,
            confidence=self.confidence,
            iou=self.iou,
            device=self.device,
            persist=True,
            verbose=False,
        )
        return self._parse(results)

    def reset(self):
        if self.model is None:
            return
        try:
            predictor = getattr(self.model, "predictor", None)
            if predictor is not None:
                predictor.trackers = None
        except Exception:
            pass

    def _parse(self, results) -> list[TraceXOpenVocabDetection]:
        detections = []
        if not results:
            return detections
        result = results[0]
        if result.boxes is None:
            return detections
        names = result.names
        for box in result.boxes:
            class_id = int(box.cls[0].item())
            confidence = float(box.conf[0].item())
            x1, y1, x2, y2 = box.xyxy[0].cpu().tolist()
            track_id = None
            if box.id is not None:
                track_id = int(box.id[0].item())
            class_name = str(names[class_id]).strip().lower()
            detections.append(
                TraceXOpenVocabDetection(
                    class_name=class_name,
                    confidence=confidence,
                    bbox=(float(x1), float(y1), float(x2), float(y2)),
                    track_id=track_id,
                )
            )
        return detections
