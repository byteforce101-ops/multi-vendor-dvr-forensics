"""TraceX Deep Vision Semantic Detector & Tracker.

Performs high-throughput semantic object detection and multi-frame tracking
for forensic investigations.

- Loads the TraceX vision weights checkpoint.
- Enforces strict forensic class filtering and cross-class spatial suppression.
- Integrates unscaled motion ROI patch detection for distant/small objects.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

# Suppress raw low-level logging from OpenCV and video modules
os.environ["OPENCV_LOG_LEVEL"] = "OFF"
os.environ["OPENCV_VIDEOIO_DEBUG"] = "0"

try:
    import cv2
    if hasattr(cv2, "utils") and hasattr(cv2.utils, "logging"):
        cv2.utils.logging.setLogLevel(cv2.utils.logging.LOG_LEVEL_SILENT)
except Exception:
    pass


class _TraceXLogFilter(logging.Filter):
    """Filter out third-party warnings mentioning OpenCV or GMC."""
    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage().lower()
        if "gmc failed" in msg or "opencv" in msg:
            return False
        return True


# Apply filter to root logger and ultralytics logger
_log_filter = _TraceXLogFilter()
logging.getLogger().addFilter(_log_filter)
logging.getLogger("ultralytics").addFilter(_log_filter)

try:
    _ultra_mod = __import__("ultralytics")
    _VisionBackend = getattr(_ultra_mod, "YOLO", None)
except ImportError:
    _VisionBackend = None


def get_default_vision_model_path() -> str:
    """Resolve the default TraceX vision model path."""
    env_path = os.getenv("TRACEX_VISION_MODEL")
    if env_path and Path(env_path).exists():
        return env_path

    # Check backend/models/tracex_vision.pt relative to codebase
    curr_dir = Path(__file__).resolve().parents[2]  # backend root
    model_candidate = curr_dir / "models" / "tracex_vision.pt"
    if model_candidate.exists():
        return str(model_candidate)

    return "tracex_vision.pt"


@dataclass
class TraceXVisionDetection:
    """Represents a discrete semantic vision detection."""

    class_id: int
    class_name: str
    confidence: float
    bbox: tuple[float, float, float, float]
    track_id: int | None = None


class TraceXVisionDetector:
    """TraceX Deep Vision Semantic Detector and Tracker."""

    def __init__(
        self,
        model_path: str | None = None,
        confidence: float = 0.30,
        iou: float = 0.50,
        device: str | None = None,
    ):
        resolved_path = model_path or get_default_vision_model_path()

        # If passed string is a legacy filename that doesn't exist directly, resolve it
        if not Path(resolved_path).exists():
            resolved_path = get_default_vision_model_path()

        if _VisionBackend is not None:
            self.model = _VisionBackend(resolved_path)
        else:
            self.model = None

        self.confidence = confidence
        self.iou = iou
        self.device = device

    # =========================================================
    # MODEL VOCABULARY
    # =========================================================

    @property
    def class_names(self) -> list[str]:
        """Return every class supported by the loaded vision model."""
        if self.model is None:
            return []

        names = self.model.names

        if isinstance(names, dict):
            return [str(names[index]) for index in sorted(names)]

        return [str(name) for name in names]

    # =========================================================
    # DETECTION
    # =========================================================

    def detect(self, frame) -> list[TraceXVisionDetection]:
        """Run single-frame semantic detection."""
        if self.model is None:
            return []

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

    def track(self, frame) -> list[TraceXVisionDetection]:
        """Run persistent multi-frame tracking using deterministic ByteTrack without GMC optical flow."""
        if self.model is None:
            return []

        results = self.model.track(
            source=frame,
            conf=self.confidence,
            iou=self.iou,
            device=self.device,
            persist=True,
            verbose=False,
            tracker="bytetrack.yaml",
        )

        return self._parse_results(results)

    # =========================================================
    # RESULT PARSING
    # =========================================================

    def _parse_results(self, results) -> list[TraceXVisionDetection]:
        detections: list[TraceXVisionDetection] = []

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

            if isinstance(names, dict):
                raw_name = str(names[class_id])
            else:
                raw_name = str(names[class_id])

            cname = raw_name.lower().strip()
            # Strict forensic class whitelist
            if cname not in {
                "person",
                "car",
                "truck",
                "bus",
                "motorcycle",
                "bicycle",
                "backpack",
                "suitcase",
                "handbag",
                "dog",
                "boat",
            }:
                continue

            min_conf = (
                max(self.confidence, 0.55)
                if cname in {"bicycle", "motorcycle"}
                else max(self.confidence, 0.40)
                if cname in {"car", "truck", "bus"}
                else self.confidence
            )
            if confidence < min_conf:
                continue

            detections.append(
                TraceXVisionDetection(
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

        # Cross-class suppression:
        vehicles = [d for d in detections if d.class_name in {"car", "truck", "bus"}]
        persons = [d for d in detections if d.class_name == "person"]

        if vehicles or persons:
            filtered: list[TraceXVisionDetection] = []
            for d in detections:
                if d.class_name in {"bicycle", "motorcycle"}:
                    in_vehicle = any(
                        self._calc_containment_ratio(d.bbox, v.bbox) > 0.30
                        or self._calc_iou(d.bbox, v.bbox) > 0.25
                        for v in vehicles
                    )
                    if in_vehicle:
                        continue

                    in_person = any(
                        self._calc_containment_ratio(d.bbox, p.bbox) > 0.35
                        or self._calc_iou(d.bbox, p.bbox) > 0.35
                        for p in persons
                    )
                    if in_person:
                        continue

                filtered.append(d)
            detections = filtered

        return detections

    @staticmethod
    def _calc_containment_ratio(
        inner_box: tuple[float, float, float, float],
        outer_box: tuple[float, float, float, float],
    ) -> float:
        ix1, iy1 = max(inner_box[0], outer_box[0]), max(inner_box[1], outer_box[1])
        ix2, iy2 = min(inner_box[2], outer_box[2]), min(inner_box[3], outer_box[3])
        iw, ih = max(0.0, ix2 - ix1), max(0.0, iy2 - iy1)
        inter = iw * ih
        inner_area = max(1.0, (inner_box[2] - inner_box[0]) * (inner_box[3] - inner_box[1]))
        return inter / inner_area

    @staticmethod
    def _calc_iou(
        box_a: tuple[float, float, float, float],
        box_b: tuple[float, float, float, float],
    ) -> float:
        ax1, ay1, ax2, ay2 = box_a
        bx1, by1, bx2, by2 = box_b
        ix1, iy1 = max(ax1, bx1), max(ay1, by1)
        ix2, iy2 = min(ax2, bx2), min(ay2, by2)
        iw, ih = max(0.0, ix2 - ix1), max(0.0, iy2 - iy1)
        inter = iw * ih
        area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
        area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
        union = area_a + area_b - inter
        return (inter / union) if union > 0 else 0.0

    # =========================================================
    # MOTION-GUIDED ROI PATCH DETECTION
    # =========================================================

    def detect_with_motion_rois(
        self,
        frame,
        motion_boxes: list[tuple[int, int, int, int]] | None = None,
        use_tracking: bool = False,
    ) -> list[TraceXVisionDetection]:
        """
        Run high-accuracy detection combining full-frame inference with
        unscaled high-resolution crops around motion regions.
        """
        import cv2

        # 1. Full-frame base detection
        base_detections = self.track(frame) if use_tracking else self.detect(frame)
        if not motion_boxes:
            return base_detections

        h, w = frame.shape[:2]
        all_candidates: list[TraceXVisionDetection] = list(base_detections)

        # 2. Process each motion ROI cluster
        for bx, by, bw, bh in motion_boxes:
            if bw < 28 or bh < 28:
                continue
            if bw > 0.85 * w and bh > 0.85 * h:
                continue

            pad_x = int(bw * 0.25)
            pad_y = int(bh * 0.25)
            x1 = max(0, bx - pad_x)
            y1 = max(0, by - pad_y)
            x2 = min(w, bx + bw + pad_x)
            y2 = min(h, by + bh + pad_y)

            crop = frame[y1:y2, x1:x2]
            if crop.shape[0] < 28 or crop.shape[1] < 28:
                continue

            crop_detections = self.detect(crop)
            for d in crop_detections:
                gx1 = min(float(w), max(0.0, d.bbox[0] + x1))
                gy1 = min(float(h), max(0.0, d.bbox[1] + y1))
                gx2 = min(float(w), max(0.0, d.bbox[2] + x1))
                gy2 = min(float(h), max(0.0, d.bbox[3] + y1))

                all_candidates.append(
                    TraceXVisionDetection(
                        class_id=d.class_id,
                        class_name=d.class_name,
                        confidence=d.confidence,
                        bbox=(gx1, gy1, gx2, gy2),
                        track_id=None,
                    )
                )

        if len(all_candidates) <= len(base_detections):
            return base_detections

        # 3. Fuse full-frame and patch detections with NMS per class
        fused_detections: list[TraceXVisionDetection] = []
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
