from ultralytics import YOLO


class YOLODetector:

    def __init__(
        self,
        model_path: str = "yolo26n.pt",
        confidence: float = 0.35,
    ):
        self.model = YOLO(model_path)
        self.confidence = confidence

    def detect(self, frame):
        results = self.model.predict(
            source=frame,
            conf=self.confidence,
            verbose=False,
        )

        return self._parse_results(results)

    def track(self, frame):
        results = self.model.track(
            source=frame,
            conf=self.confidence,
            persist=True,
            verbose=False,
        )

        return self._parse_results(results)

    def _parse_results(self, results):

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

            detections.append(
                {
                    "class_id": class_id,
                    "class_name": names[class_id],
                    "confidence": confidence,
                    "bbox": [
                        x1,
                        y1,
                        x2,
                        y2,
                    ],
                    "track_id": track_id,
                }
            )

        return detections