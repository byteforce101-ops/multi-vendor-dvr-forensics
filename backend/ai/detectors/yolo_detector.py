from __future__ import annotations

from dataclasses import dataclass

from ultralytics import YOLO


@dataclass
class YOLODetection:
    class_id: int
    class_name: str
    confidence: float
    bbox: tuple[float, float, float, float]
    track_id: int | None = None


class YOLODetector:
    """
    YOLO object detector and tracker.

    YOLO remains the primary fast detector.

    The model's complete trained vocabulary is obtained directly
    from the loaded checkpoint rather than maintaining a manually
    maintained list that could become incomplete.

    Tracking is performed with Ultralytics persist=True so that
    consecutive frames can retain object identities.
    """

    def __init__(
        self,
        model_path: str = "yolo26n.pt",
        confidence: float = 0.25,
        iou: float = 0.50,
        device: str | None = None,
    ):
        self.model = YOLO(model_path)

        self.confidence = confidence
        self.iou = iou
        self.device = device

    # =========================================================
    # MODEL VOCABULARY
    # =========================================================

    @property
    def class_names(self) -> list[str]:
        """
        Return every class supported by the loaded YOLO model.
        """

        names = self.model.names

        if isinstance(names, dict):
            return [
                str(names[index])
                for index in sorted(names)
            ]

        return [
            str(name)
            for name in names
        ]

    # =========================================================
    # DETECTION
    # =========================================================

    def detect(self, frame) -> list[YOLODetection]:

        results = self.model.predict(
            source=frame,
            conf=self.confidence,
            iou=self.iou,
            device=self.device,
            verbose=False,
        )

        return self._parse_results(results)

    # =========================================================
    # TRACKING
    # =========================================================

    def track(self, frame) -> list[YOLODetection]:

        results = self.model.track(
            source=frame,
            conf=self.confidence,
            iou=self.iou,
            device=self.device,
            persist=True,
            verbose=False,
        )

        return self._parse_results(results)

    # =========================================================
    # RESULT PARSING
    # =========================================================

    def _parse_results(
        self,
        results,
    ) -> list[YOLODetection]:

        detections: list[YOLODetection] = []

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

            if isinstance(names, dict):
                raw_name = str(names[class_id])
            else:
                raw_name = str(names[class_id])

            cname = raw_name.lower().strip()
            # Strict forensic class whitelist
            if cname not in {
                "person", "car", "truck", "bus", "motorcycle", "bicycle",
                "backpack", "suitcase", "handbag", "dog", "boat",
            }:
                continue

            detections.append(
                YOLODetection(
                    class_id=class_id,
                    class_name=cname,
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

    # =========================================================
    # MOTION-GUIDED ROI PATCH DETECTION (DVR-Scan Architecture)
    # =========================================================

    def detect_with_motion_rois(
        self,
        frame,
        motion_boxes: list[tuple[int, int, int, int]] | None = None,
        use_tracking: bool = False,
    ) -> list[YOLODetection]:
        """
        Run high-accuracy detection combining full-frame inference with
        unscaled high-resolution crops around OpenCV-detected motion regions.
        """
        import cv2

        # 1. Full-frame base detection
        base_detections = self.track(frame) if use_tracking else self.detect(frame)
        if not motion_boxes:
            return base_detections

        h, w = frame.shape[:2]
        all_candidates: list[YOLODetection] = list(base_detections)

        # 2. Process each motion ROI cluster
        for bx, by, bw, bh in motion_boxes:
            # Skip tiny noise or massive whole-frame boxes
            if bw < 28 or bh < 28:
                continue
            if bw > 0.85 * w and bh > 0.85 * h:
                continue

            # Add 25% contextual padding
            pad_x = int(bw * 0.25)
            pad_y = int(bh * 0.25)
            x1 = max(0, bx - pad_x)
            y1 = max(0, by - pad_y)
            x2 = min(w, bx + bw + pad_x)
            y2 = min(h, by + bh + pad_y)

            crop = frame[y1:y2, x1:x2]
            if crop.shape[0] < 28 or crop.shape[1] < 28:
                continue

            # Detect on unscaled high-res crop
            crop_detections = self.detect(crop)
            for d in crop_detections:
                # Map bounding box back to global frame coordinates
                gx1 = min(float(w), max(0.0, d.bbox[0] + x1))
                gy1 = min(float(h), max(0.0, d.bbox[1] + y1))
                gx2 = min(float(w), max(0.0, d.bbox[2] + x1))
                gy2 = min(float(h), max(0.0, d.bbox[3] + y1))

                all_candidates.append(
                    YOLODetection(
                        class_id=d.class_id,
                        class_name=d.class_name,
                        confidence=d.confidence,
                        bbox=(gx1, gy1, gx2, gy2),
                        track_id=None,
                    )
                )

        if len(all_candidates) <= len(base_detections):
            return base_detections

        # 3. Fuse full-frame and patch detections with OpenCV NMS per class
        fused_detections: list[YOLODetection] = []
        classes_present = {d.class_id for d in all_candidates}

        for cid in classes_present:
            class_items = [d for d in all_candidates if d.class_id == cid]
            if len(class_items) == 1:
                fused_detections.append(class_items[0])
                continue

            boxes_xywh = []
            scores = []
            for d in class_items:
                bx1, by1, bx2, by2 = d.bbox
                boxes_xywh.append([int(bx1), int(by1), int(bx2 - bx1), int(by2 - by1)])
                scores.append(float(d.confidence))

            indices = cv2.dnn.NMSBoxes(
                bboxes=boxes_xywh,
                scores=scores,
                score_threshold=self.confidence,
                nms_threshold=self.iou,
            )

            if len(indices) > 0:
                for idx in indices.flatten():
                    fused_detections.append(class_items[idx])

        return fused_detections