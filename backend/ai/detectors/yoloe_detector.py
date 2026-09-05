from __future__ import annotations

from dataclasses import dataclass

from ultralytics import YOLO


@dataclass
class YOLOEDetection:
    class_name: str
    confidence: float

    bbox: tuple[
        float,
        float,
        float,
        float,
    ]

    track_id: int | None = None


class YOLOEDetector:

    def __init__(
        self,
        model_path: str = "yoloe-26s-seg.pt",
        confidence: float = 0.15,
        iou: float = 0.50,
        device: str | None = None,
        labels: list[str] | None = None,
    ):

        self.model_path = model_path

        self.model = YOLO(
            model_path
        )

        self.confidence = confidence
        self.iou = iou
        self.device = device

        self.labels = (
            labels
            or []
        )

        if self.labels:
            self.set_classes(
                self.labels
            )

    def set_classes(
        self,
        labels: list[str],
    ):

        cleaned = []

        for label in labels:

            label = (
                str(label)
                .strip()
                .lower()
            )

            if (
                label
                and label not in cleaned
            ):
                cleaned.append(
                    label
                )

        self.labels = cleaned

        if not self.labels:
            return

        if not hasattr(
            self.model,
            "set_classes",
        ):
            raise RuntimeError(
                "The installed Ultralytics "
                "version does not expose "
                "YOLOE set_classes()."
            )

        self.model.set_classes(
            self.labels
        )

    def detect(
        self,
        frame,
    ) -> list[YOLOEDetection]:

        results = self.model.predict(
            source=frame,
            conf=self.confidence,
            iou=self.iou,
            device=self.device,
            verbose=False,
        )

        return self._parse(
            results
        )

    def track(
        self,
        frame,
    ) -> list[YOLOEDetection]:

        results = self.model.track(
            source=frame,
            conf=self.confidence,
            iou=self.iou,
            device=self.device,
            persist=True,
            verbose=False,
        )

        return self._parse(
            results
        )

    def reset(self):

        try:

            predictor = getattr(
                self.model,
                "predictor",
                None,
            )

            if predictor is not None:
                predictor.trackers = None

        except Exception:
            pass

    def _parse(
        self,
        results,
    ) -> list[YOLOEDetection]:

        detections = []

        if not results:
            return detections

        result = results[0]

        if result.boxes is None:
            return detections

        names = result.names

        for box in result.boxes:

            class_id = int(
                box.cls[0].item()
            )

            confidence = float(
                box.conf[0].item()
            )

            x1, y1, x2, y2 = (
                box.xyxy[0]
                .cpu()
                .tolist()
            )

            track_id = None

            if box.id is not None:
                track_id = int(
                    box.id[0].item()
                )

            class_name = str(
                names[class_id]
            ).strip().lower()

            detections.append(
                YOLOEDetection(
                    class_name=class_name,
                    confidence=confidence,
                    bbox=(
                        float(x1),
                        float(y1),
                        float(x2),
                        float(y2),
                    ),
                    track_id=track_id,
                )
            )

        return detections