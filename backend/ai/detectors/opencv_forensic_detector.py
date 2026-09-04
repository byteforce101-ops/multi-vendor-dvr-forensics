"""
Pure OpenCV Forensic Object Detector & Tracker.

Performs 100% local, lightweight, CPU-efficient forensic detection without
deep learning weights or external cloud dependencies:
1. OpenCV HOG Pedestrian Detector (cv2.HOGDescriptor) for people.
2. OpenCV Haar Cascades for full body and upper body.
3. OpenCV MOG2 Motion & Morphometric Aspect-Ratio Classifier for vehicles, cyclists, and moving objects.
4. Native Centroid Object Tracker across video frames.
5. Strict forensic whitelisting (zero household false positives like donuts, vases, or clocks).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

import cv2
import numpy as np

from backend.video.analysis.motion import DVRScanMotionDetector
from backend.video.enhancement.preprocessor import enhance_surveillance_frame

logger = logging.getLogger(__name__)

# Strictly forensic surveillance classes only
FORENSIC_CLASSES = {
    "person",
    "vehicle",
    "car",
    "truck",
    "bus",
    "motorcycle",
    "bicycle",
    "object",
    "motion",
}


@dataclass
class OpenCVForensicDetection:
    class_name: str
    confidence: float
    bbox: tuple[float, float, float, float]  # (x1, y1, x2, y2)
    track_id: int | None = None
    velocity: tuple[float, float] = (0.0, 0.0)  # (vx, vy) px/sec
    area: float = 0.0
    aspect_ratio: float = 0.0
    attributes: dict = field(default_factory=dict)


class OpenCVForensicDetector:
    """Pure OpenCV multi-stage forensic detector and tracker."""

    def __init__(
        self,
        confidence_threshold: float = 0.35,
        enable_hog_people: bool = True,
        enable_haar_body: bool = True,
        enable_motion_morphometrics: bool = True,
        enable_enhancement: bool = True,
        max_track_distance: float = 80.0,
        max_disappeared_frames: int = 6,
    ):
        self.confidence_threshold = confidence_threshold
        self.enable_hog_people = enable_hog_people
        self.enable_haar_body = enable_haar_body
        self.enable_motion_morphometrics = enable_motion_morphometrics
        self.enable_enhancement = enable_enhancement
        self.max_track_distance = max_track_distance
        self.max_disappeared_frames = max_disappeared_frames

        # 1. OpenCV HOG People Detector
        self.hog = None
        if enable_hog_people:
            try:
                self.hog = cv2.HOGDescriptor()
                self.hog.setSVMDetector(cv2.HOGDescriptor.getDefaultPeopleDetector())
            except Exception as exc:
                logger.debug(f"HOG detector initialization note: {exc}")

        # 2. OpenCV Haar Cascades
        self.fullbody_cascade = None
        self.upperbody_cascade = None
        if enable_haar_body:
            try:
                haar_base = cv2.data.haarcascades
                self.fullbody_cascade = cv2.CascadeClassifier(haar_base + "haarcascade_fullbody.xml")
                self.upperbody_cascade = cv2.CascadeClassifier(haar_base + "haarcascade_upperbody.xml")
            except Exception as exc:
                logger.debug(f"Haar cascade initialization note: {exc}")

        # 3. OpenCV MOG2 Motion Detector
        self.motion_detector = DVRScanMotionDetector(
            history=300,
            var_threshold=16.0,
            detect_shadows=False,
        )

        # 4. Centroid Tracker State
        self._next_track_id = 1
        self._tracked_objects: dict[int, dict] = {}  # id -> {centroid, bbox, class_name, disappeared, history}

    def reset_tracks(self) -> None:
        """Reset object tracker state between different videos."""
        self._next_track_id = 1
        self._tracked_objects = {}
        self.motion_detector = DVRScanMotionDetector(
            history=300,
            var_threshold=16.0,
            detect_shadows=False,
        )

    def detect_frame(
        self,
        frame: np.ndarray,
        fps: float = 2.0,
    ) -> list[OpenCVForensicDetection]:
        """Detect and track all forensic entities in a single frame using pure OpenCV."""
        if frame is None or frame.size == 0:
            return []

        h, w = frame.shape[:2]

        # 1. Enhance frame if enabled
        proc_frame = enhance_surveillance_frame(frame) if self.enable_enhancement else frame
        gray = cv2.cvtColor(proc_frame, cv2.COLOR_BGR2GRAY)

        candidates: list[OpenCVForensicDetection] = []

        # =====================================================
        # STAGE 1: HOG Multi-Scale Pedestrian Detection
        # =====================================================
        if self.hog is not None:
            try:
                # Downsample large frames slightly for fast HOG scanning
                hog_scale = 1.0
                hog_input = proc_frame
                if w > 1280:
                    hog_scale = 1280.0 / w
                    hog_input = cv2.resize(proc_frame, (1280, int(h * hog_scale)))

                rects, weights = self.hog.detectMultiScale(
                    hog_input,
                    winStride=(4, 4),
                    padding=(8, 8),
                    scale=1.05,
                )

                for (rx, ry, rw, rh), weight in zip(rects, weights):
                    conf = float(weight[0]) if isinstance(weight, (list, np.ndarray)) else float(weight)
                    # Normalize HOG SVM score to roughly 0.0 - 1.0
                    norm_conf = max(0.4, min(0.95, 0.5 + conf * 0.3))
                    if norm_conf >= self.confidence_threshold:
                        x1 = max(0.0, float(rx / hog_scale))
                        y1 = max(0.0, float(ry / hog_scale))
                        x2 = min(float(w), float((rx + rw) / hog_scale))
                        y2 = min(float(h), float((ry + rh) / hog_scale))
                        candidates.append(OpenCVForensicDetection(
                            class_name="person",
                            confidence=norm_conf,
                            bbox=(x1, y1, x2, y2),
                            area=float((x2 - x1) * (y2 - y1)),
                            aspect_ratio=float((y2 - y1) / max(1.0, x2 - x1)),
                            attributes={"detector": "opencv_hog"},
                        ))
            except Exception as exc:
                logger.debug(f"HOG detection note: {exc}")

        # =====================================================
        # STAGE 2: Haar Body Cascades (Complementary pose check)
        # =====================================================
        if self.fullbody_cascade is not None and not self.fullbody_cascade.empty():
            try:
                bodies = self.fullbody_cascade.detectMultiScale(
                    gray,
                    scaleFactor=1.1,
                    minNeighbors=3,
                    minSize=(30, 60),
                )
                for bx, by, bw, bh in bodies:
                    candidates.append(OpenCVForensicDetection(
                        class_name="person",
                        confidence=0.65,
                        bbox=(float(bx), float(by), float(bx + bw), float(by + bh)),
                        area=float(bw * bh),
                        aspect_ratio=float(bh / max(1.0, bw)),
                        attributes={"detector": "opencv_haar_body"},
                    ))
            except Exception as exc:
                logger.debug(f"Haar body note: {exc}")

        # =====================================================
        # STAGE 3: MOG2 Motion & Morphometric Aspect-Ratio Classification
        # =====================================================
        if self.enable_motion_morphometrics:
            motion_score, motion_boxes = self.motion_detector.process_frame(proc_frame)
            for bx, by, bw, bh in motion_boxes:
                area = float(bw * bh)
                aspect_ratio_wh = float(bw) / float(max(1, bh))
                aspect_ratio_hw = float(bh) / float(max(1, bw))

                # Skip tiny noise or full-frame flashes
                if area < 300 or (bw > 0.9 * w and bh > 0.9 * h):
                    continue

                # Forensic Classification Heuristics:
                # 1. Person: Vertical aspect ratio (h/w >= 1.35)
                if aspect_ratio_hw >= 1.35 and area <= 0.35 * w * h:
                    candidates.append(OpenCVForensicDetection(
                        class_name="person",
                        confidence=0.70,
                        bbox=(float(bx), float(by), float(bx + bw), float(by + bh)),
                        area=area,
                        aspect_ratio=aspect_ratio_hw,
                        attributes={"detector": "opencv_morphometric_person"},
                    ))
                # 2. Vehicle: Horizontal aspect ratio (w/h >= 1.1) and substantial area
                elif aspect_ratio_wh >= 1.1 and area >= 800:
                    candidates.append(OpenCVForensicDetection(
                        class_name="vehicle",
                        confidence=0.75,
                        bbox=(float(bx), float(by), float(bx + bw), float(by + bh)),
                        area=area,
                        aspect_ratio=aspect_ratio_wh,
                        attributes={"detector": "opencv_morphometric_vehicle"},
                    ))
                # 3. Bicycle / Motorcycle / Compact moving object
                elif 0.8 <= aspect_ratio_wh <= 1.35 and 400 <= area <= 6000:
                    candidates.append(OpenCVForensicDetection(
                        class_name="bicycle",
                        confidence=0.60,
                        bbox=(float(bx), float(by), float(bx + bw), float(by + bh)),
                        area=area,
                        aspect_ratio=aspect_ratio_wh,
                        attributes={"detector": "opencv_morphometric_bicycle"},
                    ))
                else:
                    candidates.append(OpenCVForensicDetection(
                        class_name="motion",
                        confidence=0.55,
                        bbox=(float(bx), float(by), float(bx + bw), float(by + bh)),
                        area=area,
                        aspect_ratio=aspect_ratio_wh,
                        attributes={"detector": "opencv_motion_cluster"},
                    ))

        # =====================================================
        # STAGE 4: Non-Maximum Suppression (NMS) Fusion
        # =====================================================
        fused = self._apply_nms(candidates)

        # =====================================================
        # STAGE 5: Centroid Tracking & Velocity Estimation
        # =====================================================
        tracked = self._update_tracks(fused, fps=fps)
        return tracked

    def _apply_nms(
        self,
        detections: list[OpenCVForensicDetection],
        iou_threshold: float = 0.45,
    ) -> list[OpenCVForensicDetection]:
        """Apply OpenCV Non-Maximum Suppression to eliminate overlapping duplicates."""
        if not detections:
            return []

        boxes = []
        scores = []
        for d in detections:
            x1, y1, x2, y2 = d.bbox
            boxes.append([int(x1), int(y1), int(x2 - x1), int(y2 - y1)])
            scores.append(float(d.confidence))

        indices = cv2.dnn.NMSBoxes(
            bboxes=boxes,
            scores=scores,
            score_threshold=self.confidence_threshold,
            nms_threshold=iou_threshold,
        )

        fused: list[OpenCVForensicDetection] = []
        if len(indices) > 0:
            for idx in indices.flatten():
                fused.append(detections[idx])

        return fused

    def _update_tracks(
        self,
        detections: list[OpenCVForensicDetection],
        fps: float = 2.0,
    ) -> list[OpenCVForensicDetection]:
        """Track centroids across consecutive frames and estimate velocity vectors with predictive motion."""
        if not detections:
            # Mark existing tracks as disappeared
            for tid in list(self._tracked_objects.keys()):
                self._tracked_objects[tid]["disappeared"] += 1
                if self._tracked_objects[tid]["disappeared"] > self.max_disappeared_frames:
                    del self._tracked_objects[tid]
            return []

        # Current frame centroids and bboxes
        current_centroids = []
        current_bboxes = []
        for d in detections:
            x1, y1, x2, y2 = d.bbox
            cx = (x1 + x2) / 2.0
            cy = (y1 + y2) / 2.0
            current_centroids.append((cx, cy))
            current_bboxes.append(d.bbox)

        # If no existing tracks, initialize all
        if not self._tracked_objects:
            for i, d in enumerate(detections):
                tid = self._next_track_id
                self._next_track_id += 1
                cx, cy = current_centroids[i]
                d.track_id = tid
                self._tracked_objects[tid] = {
                    "centroid": (cx, cy),
                    "bbox": d.bbox,
                    "class_name": d.class_name,
                    "disappeared": 0,
                    "velocity": (0.0, 0.0),
                    "history": [(cx, cy)],
                }
            return detections

        dt = 1.0 / max(0.1, fps)
        track_ids = list(self._tracked_objects.keys())

        # Adaptive search radius for high-resolution / fast-moving footage (vehicles, dashcam)
        effective_max_dist = max(self.max_track_distance, 220.0)

        # Compute cost/distance matrix between predictions and new detections
        cost_candidates: list[tuple[float, int, int]] = []  # (cost, d_idx, tid)

        for d_idx, (cx, cy) in enumerate(current_centroids):
            d_bbox = current_bboxes[d_idx]
            d_cls = detections[d_idx].class_name

            for tid in track_ids:
                track = self._tracked_objects[tid]
                px, py = track["centroid"]
                vx, vy = track.get("velocity", (0.0, 0.0))

                # Extrapolate expected position
                pred_x = px + vx * dt
                pred_y = py + vy * dt

                # Compute distance to predicted centroid as well as last centroid
                dist_pred = float(np.hypot(cx - pred_x, cy - pred_y))
                dist_prev = float(np.hypot(cx - px, cy - py))
                base_dist = min(dist_pred, dist_prev)

                # IoU overlap affinity
                prev_bbox = track["bbox"]
                ix1 = max(d_bbox[0], prev_bbox[0])
                iy1 = max(d_bbox[1], prev_bbox[1])
                ix2 = min(d_bbox[2], prev_bbox[2])
                iy2 = min(d_bbox[3], prev_bbox[3])
                iw = max(0.0, ix2 - ix1)
                ih = max(0.0, iy2 - iy1)
                inter = iw * ih
                area_a = max(1.0, (d_bbox[2] - d_bbox[0]) * (d_bbox[3] - d_bbox[1]))
                area_b = max(1.0, (prev_bbox[2] - prev_bbox[0]) * (prev_bbox[3] - prev_bbox[1]))
                iou = inter / (area_a + area_b - inter) if (area_a + area_b - inter) > 0 else 0.0

                # Score penalty/bonus
                cost = base_dist * (1.0 - 0.5 * iou)
                if track["class_name"] != d_cls and d_cls not in ("object", "motion") and track["class_name"] not in ("object", "motion"):
                    cost += 50.0  # slight class mismatch penalty

                if base_dist <= effective_max_dist or iou > 0.15:
                    cost_candidates.append((cost, d_idx, tid))

        # Greedy match by minimum cost
        cost_candidates.sort(key=lambda x: x[0])
        matched_tracks = set()
        matched_detections = set()

        for cost, d_idx, tid in cost_candidates:
            if d_idx in matched_detections or tid in matched_tracks:
                continue

            matched_tracks.add(tid)
            matched_detections.add(d_idx)
            d = detections[d_idx]
            d.track_id = tid

            cx, cy = current_centroids[d_idx]
            px, py = self._tracked_objects[tid]["centroid"]
            meas_vx = (cx - px) / dt
            meas_vy = (cy - py) / dt

            # Smooth velocity with exponential moving average
            prev_vx, prev_vy = self._tracked_objects[tid].get("velocity", (0.0, 0.0))
            if abs(prev_vx) > 0.0 or abs(prev_vy) > 0.0:
                smooth_vx = 0.75 * meas_vx + 0.25 * prev_vx
                smooth_vy = 0.75 * meas_vy + 0.25 * prev_vy
            else:
                smooth_vx = meas_vx
                smooth_vy = meas_vy

            d.velocity = (smooth_vx, smooth_vy)

            hist = self._tracked_objects[tid]["history"]
            hist.append((cx, cy))
            if len(hist) > 30:
                hist.pop(0)

            # Keep stronger class name
            best_class = d.class_name if d.class_name not in ("object", "motion") else self._tracked_objects[tid]["class_name"]

            self._tracked_objects[tid] = {
                "centroid": (cx, cy),
                "bbox": d.bbox,
                "class_name": best_class,
                "disappeared": 0,
                "velocity": (smooth_vx, smooth_vy),
                "history": hist,
            }

        # Unmatched detections become new tracks
        for d_idx, d in enumerate(detections):
            if d_idx not in matched_detections:
                tid = self._next_track_id
                self._next_track_id += 1
                cx, cy = current_centroids[d_idx]
                d.track_id = tid
                self._tracked_objects[tid] = {
                    "centroid": (cx, cy),
                    "bbox": d.bbox,
                    "class_name": d.class_name,
                    "disappeared": 0,
                    "velocity": (0.0, 0.0),
                    "history": [(cx, cy)],
                }

        # Unmatched existing tracks increment disappeared counter
        for tid in track_ids:
            if tid not in matched_tracks:
                self._tracked_objects[tid]["disappeared"] += 1
                if self._tracked_objects[tid]["disappeared"] > self.max_disappeared_frames:
                    del self._tracked_objects[tid]

        return detections
