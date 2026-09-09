"""backend/ai/pipeline/tracex_ai_engine.py — TraceX AI & Detection Engine.

Provides the unified TraceX application-level AI engine:
- Multi-model forensic detection orchestration (Deep vision + Open vocabulary + Pure forensic detection).
- Surveillance enhancement preprocessing (CLAHE, gamma adjustment, unsharp masking).
- Motion-guided high-resolution ROI patching.
- Spatio-temporal track association and entity identification.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

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
from backend.video.analysis.motion import DVRScanMotionDetector
from backend.video.enhancement.preprocessor import enhance_surveillance_frame
from backend.video.extraction.frame_extractor import FrameSample

logger = logging.getLogger(__name__)


# =============================================================
# TRACEX DETECTION RESULT MODEL
# =============================================================


@dataclass
class TraceXDetectionResult:
    """Represents a discrete forensic object detection produced by the TraceX AI Engine."""

    frame_number: int
    timestamp_seconds: float

    object_type: str
    confidence: float

    bbox: tuple[float, float, float, float]

    track_id: int | None

    # Detection provenance
    source: str = "forensic"

    # Open vocabulary confidence
    dino_confidence: float | None = None

    # True when primary vision detector and open-vocabulary confirmation agree
    verified: bool = False

    # Unique entity identifier
    entity_id: str | None = None

    # Kinematic trajectory & attributes
    velocity: tuple[float, float] = (0.0, 0.0)
    attributes: dict = field(default_factory=dict)


# Backward compatibility alias
AIDetectionResult = TraceXDetectionResult


# =============================================================
# TRACEX AI ENGINE
# =============================================================


class TraceXAIEngine:
    """
    TraceX AI Detection & Intelligence Engine.

    Orchestrates multi-model forensic object detection and tracking across
    video evidence streams:

    1. TraceX Deep Vision Semantic Detector:
        - High-throughput forensic semantic object detection.
        - Provides continuous multi-frame object tracking.
    2. TraceX Open-Vocabulary Discovery Detector (Grounding DINO):
        - Discovers specialized or rare forensic objects beyond fixed vocabularies.
        - Sampled periodically to maximize CPU/GPU efficiency.
    3. TraceX Pure Forensic Detector:
        - 100% local, weightless pedestrian HOG, Haar cascades, and MOG2 morphometrics.
        - Operates as a fast standalone engine or fallback.
    4. Motion-Guided ROI Patching & Enhancement:
        - Preprocesses low-light/noisy surveillance frames with CLAHE and gamma correction.
        - Routes high-motion regions for focused high-resolution inspection.
    """

    # =========================================================
    # PRIMARY SEMANTIC THRESHOLDS
    # =========================================================

    STRONG_DETECTION_THRESHOLD = 0.65

    # =========================================================
    # OPEN-VOCABULARY DISCOVERY THRESHOLDS
    # =========================================================

    DINO_THRESHOLD = 0.20
    DINO_TEXT_THRESHOLD = 0.15
    DINO_IOU_MATCH_THRESHOLD = 0.25

    # Run open-vocabulary discovery every N sampled frames
    DINO_DISCOVERY_INTERVAL = 2

    # =========================================================
    # OPEN-VOCABULARY TRACKING
    # =========================================================

    DINO_TRACK_IOU_THRESHOLD = 0.30
    DINO_TRACK_MAX_GAP_FRAMES = 6

    # =========================================================
    # BROAD OPEN-VOCABULARY FORENSIC VOCABULARY
    # =========================================================

    DINO_VOCABULARY = {
        # People
        "person",
        "child",
        "baby",
        "adult",
        "man",
        "woman",
        # Vehicles
        "car",
        "taxi",
        "truck",
        "pickup truck",
        "van",
        "bus",
        "minibus",
        "motorcycle",
        "motorbike",
        "scooter",
        "bicycle",
        "bike",
        "ambulance",
        "police car",
        "fire truck",
        "tractor",
        # Bags
        "bag",
        "handbag",
        "purse",
        "backpack",
        "school bag",
        "shoulder bag",
        "tote bag",
        "suitcase",
        "luggage",
        "briefcase",
        "duffel bag",
        "shopping bag",
        "plastic bag",
        # Personal items
        "wallet",
        "purse",
        "key",
        "keys",
        "watch",
        "glasses",
        "sunglasses",
        "hat",
        "cap",
        "helmet",
        "shoe",
        "umbrella",
        # Electronics
        "cell phone",
        "mobile phone",
        "smartphone",
        "phone",
        "laptop",
        "computer",
        "tablet",
        "monitor",
        "television",
        "camera",
        "remote control",
        "keyboard",
        "mouse",
        "headphones",
        "earphones",
        # Documents / Small items
        "book",
        "notebook",
        "paper",
        "document",
        "newspaper",
        "folder",
        "box",
        "package",
        "parcel",
        "cardboard box",
        # Bottles / Containers
        "bottle",
        "water bottle",
        "plastic bottle",
        "glass bottle",
        "cup",
        "mug",
        "glass",
        "can",
        "container",
        "bucket",
        "basket",
        # Furniture
        "chair",
        "table",
        "desk",
        "sofa",
        "couch",
        "bed",
        "bench",
        "cabinet",
        "shelf",
        "drawer",
        # Tools / Equipment
        "tool",
        "hammer",
        "screwdriver",
        "drill",
        "ladder",
        "broom",
        "mop",
        "dustbin",
        "trash can",
        # Clothing
        "shirt",
        "t-shirt",
        "jacket",
        "coat",
        "pants",
        "trousers",
        "shorts",
        "dress",
        "skirt",
        "clothing",
        # Common forensic objects
        "knife",
        "scissors",
        "stick",
        "rope",
        "chain",
        "barrier",
        "traffic cone",
        "sign",
        "license plate",
        "door",
        "window",
        "gate",
        # Animals
        "dog",
        "cat",
        "bird",
        "horse",
        "cow",
        "sheep",
        "goat",
        # Other common scene objects
        "bicycle helmet",
        "stroller",
        "shopping cart",
        "cart",
        "wheelchair",
        "fire extinguisher",
        "street light",
        "lamp",
        "plant",
        "flower pot",
    }

    # =========================================================
    # LABEL NORMALIZATION ALIASES
    # =========================================================

    LABEL_ALIASES = {
        "people": "person",
        "a person": "person",
        "motorbike": "motorcycle",
        "a motorcycle": "motorcycle",
        "bike": "bicycle",
        "a bicycle": "bicycle",
        "phone": "cell phone",
        "mobile phone": "cell phone",
        "smartphone": "cell phone",
        "purse": "handbag",
        "a handbag": "handbag",
        "a backpack": "backpack",
        "a suitcase": "suitcase",
        "a bottle": "bottle",
        "water bottle": "bottle",
        "a car": "car",
        "a truck": "truck",
        "a bus": "bus",
    }

    def __init__(
        self,
        model_path: str | None = None,
        confidence: float = 0.50,
        iou: float = 0.50,
        device: str | None = None,
        enable_grounding_dino: bool = False,
        enable_enhancement: bool = True,
        enable_motion_rois: bool = True,
        detector_engine: str = "vision",  # "vision" | "forensic" | "hybrid"
    ):
        norm_engine = detector_engine.lower()
        if norm_engine not in ("vision", "forensic", "hybrid"):
            norm_engine = "vision"

        self.detector_engine = norm_engine

        # -----------------------------------------------------
        # TraceX Pure Forensic Detector
        # -----------------------------------------------------
        self.forensic_detector = (
            TraceXForensicDetector(
                confidence_threshold=confidence,
                enable_enhancement=enable_enhancement,
            )
            if norm_engine in ("forensic", "hybrid", "vision")
            else None
        )

        # -----------------------------------------------------
        # TraceX Deep Vision Semantic Detector
        # -----------------------------------------------------
        self.vision_detector = None
        if norm_engine in ("vision", "hybrid"):
            try:
                self.vision_detector = TraceXVisionDetector(
                    model_path=model_path,
                    confidence=confidence,
                    iou=iou,
                    device=device,
                )
            except Exception as exc:
                logger.debug(f"TraceX Vision detector load notice: {exc}")

        # -----------------------------------------------------
        # Enhancement & Motion-Guided ROI
        # -----------------------------------------------------
        self.enable_enhancement = enable_enhancement
        self.enable_motion_rois = enable_motion_rois
        self.motion_detector = (
            DVRScanMotionDetector()
            if enable_motion_rois
            else None
        )

        # -----------------------------------------------------
        # Open-Vocabulary Discovery (Grounding DINO)
        # -----------------------------------------------------
        self.enable_grounding_dino = enable_grounding_dino
        self.dino = None
        if enable_grounding_dino:
            self.dino = GroundingDINODetector(
                confidence=self.DINO_THRESHOLD,
                text_confidence=self.DINO_TEXT_THRESHOLD,
                device=device,
            )

        # -----------------------------------------------------
        # Open-Vocabulary Object Tracking
        # -----------------------------------------------------
        self._next_dino_track_id = -1
        self._dino_tracks: dict[int, dict] = {}

    # =========================================================
    # LABEL NORMALISATION
    # =========================================================

    @classmethod
    def _normalise_label(cls, label: str) -> str:
        label = str(label).lower().strip()
        return cls.LABEL_ALIASES.get(label, label)

    # =========================================================
    # IOU
    # =========================================================

    @staticmethod
    def _iou(box_a, box_b) -> float:
        ax1, ay1, ax2, ay2 = box_a
        bx1, by1, bx2, by2 = box_b

        ix1 = max(ax1, bx1)
        iy1 = max(ay1, by1)
        ix2 = min(ax2, bx2)
        iy2 = min(ay2, by2)

        width = max(0.0, ix2 - ix1)
        height = max(0.0, iy2 - iy1)

        intersection = width * height
        area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
        area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
        union = area_a + area_b - intersection

        if union <= 0:
            return 0.0

        return intersection / union

    # =========================================================
    # CENTROID
    # =========================================================

    @staticmethod
    def _centroid(box):
        x1, y1, x2, y2 = box
        return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)

    # =========================================================
    # DINO → VISION MATCH
    # =========================================================

    def _find_vision_match(self, vision_detection, dino_detections):
        v_label = self._normalise_label(vision_detection.class_name)
        best = None
        best_iou = 0.0

        for dino in dino_detections:
            dino_label = self._normalise_label(dino["label"])
            if dino_label != v_label:
                continue

            current_iou = self._iou(vision_detection.bbox, dino["bbox"])
            if current_iou > best_iou:
                best_iou = current_iou
                best = dino

        if best is not None and best_iou >= self.DINO_IOU_MATCH_THRESHOLD:
            return best, best_iou

        return None, 0.0

    # =========================================================
    # OPEN-VOCABULARY TRACK ASSOCIATION
    # =========================================================

    def _assign_dino_track(
        self,
        label: str,
        bbox,
        frame_number: int,
    ) -> int:
        label = self._normalise_label(label)
        best_track_id = None
        best_iou = 0.0

        for track_id, track in self._dino_tracks.items():
            if track["label"] != label:
                continue

            if frame_number - track["frame_number"] > self.DINO_TRACK_MAX_GAP_FRAMES:
                continue

            current_iou = self._iou(bbox, track["bbox"])
            if current_iou > best_iou:
                best_iou = current_iou
                best_track_id = track_id

        if best_track_id is not None and best_iou >= self.DINO_TRACK_IOU_THRESHOLD:
            self._dino_tracks[best_track_id] = {
                "label": label,
                "bbox": bbox,
                "frame_number": frame_number,
            }
            return best_track_id

        track_id = self._next_dino_track_id
        self._next_dino_track_id -= 1

        self._dino_tracks[track_id] = {
            "label": label,
            "bbox": bbox,
            "frame_number": frame_number,
        }

        return track_id

    # =========================================================
    # ENTITY ID
    # =========================================================

    @staticmethod
    def _entity_id(object_type: str, track_id: int | None) -> str:
        if track_id is None:
            return object_type
        return f"{object_type}#{track_id}"

    # =========================================================
    # MAIN ANALYSIS PIPELINE
    # =========================================================

    def analyze_frames(
        self,
        frames: list[FrameSample],
    ) -> list[TraceXDetectionResult]:
        """Process video frame samples through the TraceX AI Engine pipeline."""
        results: list[TraceXDetectionResult] = []
        dino_labels = sorted(self.DINO_VOCABULARY)

        for frame_index, frame in enumerate(frames):
            # Preprocess and enhance surveillance frame (CLAHE, gamma correction)
            processed_image = (
                enhance_surveillance_frame(frame.image)
                if self.enable_enhancement
                else frame.image
            )

            # Extract motion regions for high-res ROI patching
            motion_boxes = None
            if self.enable_motion_rois and self.motion_detector is not None:
                _, motion_boxes = self.motion_detector.process_frame(processed_image)

            # =================================================
            # 1. PURE FORENSIC DETECTION (or fallback)
            # =================================================
            if (self.detector_engine == "forensic" or self.vision_detector is None) and self.forensic_detector is not None:
                forensic_detections = self.forensic_detector.detect_frame(frame.image, fps=2.0)
                for det in forensic_detections:
                    obj_type = self._normalise_label(det.class_name)
                    results.append(
                        TraceXDetectionResult(
                            frame_number=frame.frame_number,
                            timestamp_seconds=frame.timestamp_seconds,
                            object_type=obj_type,
                            confidence=det.confidence,
                            bbox=det.bbox,
                            track_id=det.track_id,
                            source="forensic",
                            dino_confidence=None,
                            verified=True,
                            entity_id=self._entity_id(obj_type, det.track_id),
                            velocity=det.velocity,
                            attributes=det.attributes,
                        )
                    )
                continue

            # =================================================
            # 2. DEEP VISION DETECTION (with Motion-Guided ROI Patching)
            # =================================================
            if self.vision_detector is not None:
                if self.enable_motion_rois and motion_boxes:
                    vision_detections = self.vision_detector.detect_with_motion_rois(
                        processed_image,
                        motion_boxes=motion_boxes,
                        use_tracking=True,
                    )
                else:
                    vision_detections = self.vision_detector.track(processed_image)
            else:
                vision_detections = []

            # =================================================
            # 3. OPEN-VOCABULARY DISCOVERY (DINO)
            # =================================================
            dino_detections = []
            run_dino = (
                self.enable_grounding_dino
                and self.dino is not None
                and (frame_index % self.DINO_DISCOVERY_INTERVAL == 0)
            )

            if run_dino:
                dino_detections = self.dino.detect(frame.image, dino_labels)

            matched_dino_indexes: set[int] = set()

            # =================================================
            # 4. PRIMARY VISION OBJECT PROCESSING
            # =================================================
            for v_det in vision_detections:
                object_type = self._normalise_label(v_det.class_name)
                dino_match = None
                dino_iou = 0.0
                dino_index = None

                if dino_detections:
                    best = None
                    best_iou = 0.0
                    best_index = None

                    for index, dino in enumerate(dino_detections):
                        if index in matched_dino_indexes:
                            continue

                        dino_label = self._normalise_label(dino["label"])
                        if dino_label != object_type:
                            continue

                        current_iou = self._iou(v_det.bbox, dino["bbox"])
                        if current_iou > best_iou:
                            best = dino
                            best_iou = current_iou
                            best_index = index

                    if best is not None and best_iou >= self.DINO_IOU_MATCH_THRESHOLD:
                        dino_match = best
                        dino_iou = best_iou
                        dino_index = best_index

                if dino_index is not None:
                    matched_dino_indexes.add(dino_index)

                # Strong vision detection
                if v_det.confidence >= self.STRONG_DETECTION_THRESHOLD:
                    results.append(
                        TraceXDetectionResult(
                            frame_number=frame.frame_number,
                            timestamp_seconds=frame.timestamp_seconds,
                            object_type=object_type,
                            confidence=v_det.confidence,
                            bbox=v_det.bbox,
                            track_id=v_det.track_id,
                            source="vision+dino" if dino_match else "vision",
                            dino_confidence=dino_match["confidence"] if dino_match else None,
                            verified=dino_match is not None,
                            entity_id=self._entity_id(object_type, v_det.track_id),
                        )
                    )
                    continue

                # Open-vocabulary confirms weaker vision detection
                if dino_match is not None:
                    results.append(
                        TraceXDetectionResult(
                            frame_number=frame.frame_number,
                            timestamp_seconds=frame.timestamp_seconds,
                            object_type=object_type,
                            confidence=v_det.confidence,
                            bbox=v_det.bbox,
                            track_id=v_det.track_id,
                            source="vision+dino",
                            dino_confidence=dino_match["confidence"],
                            verified=True,
                            entity_id=self._entity_id(object_type, v_det.track_id),
                        )
                    )

            # =================================================
            # 5. OPEN-VOCABULARY ONLY DISCOVERIES
            # =================================================
            for index, dino in enumerate(dino_detections):
                if index in matched_dino_indexes:
                    continue

                label = self._normalise_label(dino["label"])
                bbox = tuple(float(value) for value in dino["bbox"])
                confidence = float(dino["confidence"])

                # Suppress false positive bicycle detections inside vehicles or persons
                if label in {"bicycle", "motorcycle"}:
                    overlaps_existing = any(
                        r.frame_number == frame.frame_number
                        and r.object_type in {"car", "truck", "bus", "vehicle", "person"}
                        and (
                            self._iou(bbox, r.bbox) > 0.30
                            or (
                                bbox[0] >= r.bbox[0]
                                and bbox[1] >= r.bbox[1]
                                and bbox[2] <= r.bbox[2]
                                and bbox[3] <= r.bbox[3]
                            )
                        )
                        for r in results
                    )
                    if overlaps_existing:
                        continue

                # Assign track ID for open-vocabulary discovered objects
                track_id = self._assign_dino_track(label, bbox, frame.frame_number)

                results.append(
                    TraceXDetectionResult(
                        frame_number=frame.frame_number,
                        timestamp_seconds=frame.timestamp_seconds,
                        object_type=label,
                        confidence=confidence,
                        bbox=bbox,
                        track_id=track_id,
                        source="grounding_dino",
                        dino_confidence=confidence,
                        verified=True,
                        entity_id=self._entity_id(label, track_id),
                    )
                )

        return results


# Backward compatibility alias
AIService = TraceXAIEngine
