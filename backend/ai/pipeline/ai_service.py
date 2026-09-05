from __future__ import annotations

from dataclasses import dataclass, field

from backend.ai.detectors.grounding_dino_detector import (
    GroundingDINODetector,
)

from backend.ai.detectors.yolo_detector import (
    YOLODetector,
)

from backend.video.extraction.frame_extractor import (
    FrameSample,
)

from backend.video.enhancement.preprocessor import (
    enhance_surveillance_frame,
)

from backend.video.analysis.motion import (
    DVRScanMotionDetector,
)

from backend.ai.detectors.opencv_forensic_detector import (
    OpenCVForensicDetector,
)


# =============================================================
# RESULT MODEL
# =============================================================


@dataclass
class AIDetectionResult:
    frame_number: int
    timestamp_seconds: float

    object_type: str
    confidence: float

    bbox: tuple[float, float, float, float]

    track_id: int | None

    # Detection provenance
    source: str = "opencv"

    # Grounding DINO confidence
    dino_confidence: float | None = None

    # True when YOLO and DINO agree
    verified: bool = False

    # Unique entity identifier
    entity_id: str | None = None

    # Kinematic trajectory & attributes
    velocity: tuple[float, float] = (0.0, 0.0)
    attributes: dict = field(default_factory=dict)


# =============================================================
# AI SERVICE
# =============================================================


class AIService:
    """
    Multi-model forensic object detection pipeline.

    YOLO:
        - fast
        - detects every class supported by its checkpoint
        - provides object tracking

    Grounding DINO:
        - open-vocabulary detection
        - searches for objects YOLO may miss
        - used periodically because it is much slower on CPU

    Fusion:
        - combines YOLO and DINO
        - preserves individual objects
        - preserves bounding boxes
        - preserves track IDs
        - assigns IDs to DINO-only objects
    """

    # =========================================================
    # YOLO STRONG DETECTION
    # =========================================================

    STRONG_YOLO_THRESHOLD = 0.65

    # =========================================================
    # DINO
    # =========================================================

    DINO_THRESHOLD = 0.20

    DINO_TEXT_THRESHOLD = 0.15

    DINO_IOU_MATCH_THRESHOLD = 0.25

    # Run DINO every N sampled frames.

    # At 2 FPS:
    #
    # 1 = every 0.5 sec
    # 2 = every 1 sec
    # 4 = every 2 sec
    #
    # CPU performance is the reason this is not every frame.

    DINO_DISCOVERY_INTERVAL = 2

    # =========================================================
    # DINO TRACKING
    # =========================================================

    DINO_TRACK_IOU_THRESHOLD = 0.30

    DINO_TRACK_MAX_GAP_FRAMES = 6

    # =========================================================
    # BROAD OPEN-VOCABULARY FORENSIC VOCABULARY
    # =========================================================

    DINO_VOCABULARY = {

        # -----------------------------------------------------
        # PEOPLE
        # -----------------------------------------------------

        "person",
        "child",
        "baby",
        "adult",
        "man",
        "woman",

        # -----------------------------------------------------
        # VEHICLES
        # -----------------------------------------------------

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

        # -----------------------------------------------------
        # BAGS
        # -----------------------------------------------------

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

        # -----------------------------------------------------
        # PERSONAL ITEMS
        # -----------------------------------------------------

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

        # -----------------------------------------------------
        # ELECTRONICS
        # -----------------------------------------------------

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

        # -----------------------------------------------------
        # DOCUMENTS / SMALL ITEMS
        # -----------------------------------------------------

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

        # -----------------------------------------------------
        # BOTTLES / CONTAINERS
        # -----------------------------------------------------

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

        # -----------------------------------------------------
        # FURNITURE
        # -----------------------------------------------------

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

        # -----------------------------------------------------
        # TOOLS / EQUIPMENT
        # -----------------------------------------------------

        "tool",
        "hammer",
        "screwdriver",
        "drill",
        "ladder",
        "broom",
        "mop",
        "dustbin",
        "trash can",

        # -----------------------------------------------------
        # CLOTHING
        # -----------------------------------------------------

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

        # -----------------------------------------------------
        # COMMON FORENSIC OBJECTS
        # -----------------------------------------------------

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

        # -----------------------------------------------------
        # ANIMALS
        # -----------------------------------------------------

        "dog",
        "cat",
        "bird",
        "horse",
        "cow",
        "sheep",
        "goat",

        # -----------------------------------------------------
        # OTHER COMMON SCENE OBJECTS
        # -----------------------------------------------------

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
    # LABEL ALIASES
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
        model_path: str = "yolo26n.pt",
        confidence: float = 0.50,
        iou: float = 0.50,
        device: str | None = None,
        enable_grounding_dino: bool = False,
        enable_enhancement: bool = True,
        enable_motion_rois: bool = True,
        detector_engine: str = "opencv",  # "opencv" | "hybrid" | "yolo"
    ):
        self.detector_engine = detector_engine

        # -----------------------------------------------------
        # OPENCV PURE FORENSIC DETECTOR
        # -----------------------------------------------------

        self.opencv_detector = (
            OpenCVForensicDetector(
                confidence_threshold=confidence,
                enable_enhancement=enable_enhancement,
            )
            if detector_engine in ("opencv", "hybrid")
            else None
        )

        # -----------------------------------------------------
        # YOLO (Optional / Hybrid)
        # -----------------------------------------------------

        self.yolo = None
        if detector_engine in ("yolo", "hybrid"):
            try:
                self.yolo = YOLODetector(
                    model_path=model_path,
                    confidence=confidence,
                    iou=iou,
                    device=device,
                )
            except Exception as exc:
                logger.debug(f"YOLO detector load notice: {exc}")

        # -----------------------------------------------------
        # OPENCV ENHANCEMENT & MOTION-GUIDED ROI
        # -----------------------------------------------------

        self.enable_enhancement = enable_enhancement
        self.enable_motion_rois = enable_motion_rois
        self.motion_detector = (
            DVRScanMotionDetector()
            if enable_motion_rois
            else None
        )

        # -----------------------------------------------------
        # DINO
        # -----------------------------------------------------

        self.enable_grounding_dino = (
            enable_grounding_dino
        )

        self.dino = None

        if enable_grounding_dino:

            self.dino = GroundingDINODetector(
                confidence=self.DINO_THRESHOLD,
                text_confidence=self.DINO_TEXT_THRESHOLD,
                device=device,
            )

        # -----------------------------------------------------
        # DINO-only object tracker
        # -----------------------------------------------------

        self._next_dino_track_id = -1

        self._dino_tracks: dict[
            int,
            dict
        ] = {}

    # =========================================================
    # LABEL NORMALISATION
    # =========================================================

    @classmethod
    def _normalise_label(
        cls,
        label: str,
    ) -> str:

        label = (
            str(label)
            .lower()
            .strip()
        )

        return cls.LABEL_ALIASES.get(
            label,
            label,
        )

    # =========================================================
    # IOU
    # =========================================================

    @staticmethod
    def _iou(
        box_a,
        box_b,
    ) -> float:

        ax1, ay1, ax2, ay2 = box_a
        bx1, by1, bx2, by2 = box_b

        ix1 = max(ax1, bx1)
        iy1 = max(ay1, by1)

        ix2 = min(ax2, bx2)
        iy2 = min(ay2, by2)

        width = max(
            0.0,
            ix2 - ix1,
        )

        height = max(
            0.0,
            iy2 - iy1,
        )

        intersection = (
            width * height
        )

        area_a = (
            max(0.0, ax2 - ax1)
            * max(0.0, ay2 - ay1)
        )

        area_b = (
            max(0.0, bx2 - bx1)
            * max(0.0, by2 - by1)
        )

        union = (
            area_a
            + area_b
            - intersection
        )

        if union <= 0:
            return 0.0

        return intersection / union

    # =========================================================
    # CENTROID
    # =========================================================

    @staticmethod
    def _centroid(box):

        x1, y1, x2, y2 = box

        return (
            (x1 + x2) / 2.0,
            (y1 + y2) / 2.0,
        )

    # =========================================================
    # DINO → YOLO MATCH
    # =========================================================

    def _find_yolo_match(
        self,
        yolo_detection,
        dino_detections,
    ):

        yolo_label = self._normalise_label(
            yolo_detection.class_name
        )

        best = None
        best_iou = 0.0

        for dino in dino_detections:

            dino_label = self._normalise_label(
                dino["label"]
            )

            if dino_label != yolo_label:
                continue

            current_iou = self._iou(
                yolo_detection.bbox,
                dino["bbox"],
            )

            if current_iou > best_iou:

                best_iou = current_iou
                best = dino

        if (
            best is not None
            and best_iou
            >= self.DINO_IOU_MATCH_THRESHOLD
        ):
            return best, best_iou

        return None, 0.0

    # =========================================================
    # DINO TRACK ASSOCIATION
    # =========================================================

    def _assign_dino_track(
        self,
        label: str,
        bbox,
        frame_number: int,
    ) -> int:

        label = self._normalise_label(
            label
        )

        best_track_id = None
        best_iou = 0.0

        for track_id, track in self._dino_tracks.items():

            if track["label"] != label:
                continue

            if (
                frame_number
                - track["frame_number"]
                > self.DINO_TRACK_MAX_GAP_FRAMES
            ):
                continue

            current_iou = self._iou(
                bbox,
                track["bbox"],
            )

            if (
                current_iou
                > best_iou
            ):

                best_iou = current_iou
                best_track_id = track_id

        if (
            best_track_id is not None
            and best_iou
            >= self.DINO_TRACK_IOU_THRESHOLD
        ):

            self._dino_tracks[
                best_track_id
            ] = {
                "label": label,
                "bbox": bbox,
                "frame_number": frame_number,
            }

            return best_track_id

        track_id = (
            self._next_dino_track_id
        )

        self._next_dino_track_id -= 1

        self._dino_tracks[
            track_id
        ] = {
            "label": label,
            "bbox": bbox,
            "frame_number": frame_number,
        }

        return track_id

    # =========================================================
    # ENTITY ID
    # =========================================================

    @staticmethod
    def _entity_id(
        object_type: str,
        track_id: int | None,
    ) -> str:

        if track_id is None:
            return object_type

        return (
            f"{object_type}#{track_id}"
        )

    # =========================================================
    # MAIN ANALYSIS
    # =========================================================

    def analyze_frames(
        self,
        frames: list[FrameSample],
    ) -> list[AIDetectionResult]:

        results: list[
            AIDetectionResult
        ] = []

        dino_labels = sorted(
            self.DINO_VOCABULARY
        )

        # -----------------------------------------------------
        # FRAME PROCESSING
        # -----------------------------------------------------

        for frame_index, frame in enumerate(frames):

            # Preprocess and enhance surveillance frame (CLAHE, gamma correction)
            processed_image = (
                enhance_surveillance_frame(frame.image)
                if self.enable_enhancement
                else frame.image
            )

            # Extract OpenCV MOG2 motion regions for high-res ROI patching
            motion_boxes = None
            if self.enable_motion_rois and self.motion_detector is not None:
                _, motion_boxes = self.motion_detector.process_frame(processed_image)

            # =================================================
            # 1. PURE OPENCV FORENSIC DETECTION
            # =================================================
            if self.detector_engine == "opencv" and self.opencv_detector is not None:
                opencv_detections = self.opencv_detector.detect_frame(frame.image, fps=2.0)
                for det in opencv_detections:
                    obj_type = self._normalise_label(det.class_name)
                    results.append(
                        AIDetectionResult(
                            frame_number=frame.frame_number,
                            timestamp_seconds=frame.timestamp_seconds,
                            object_type=obj_type,
                            confidence=det.confidence,
                            bbox=det.bbox,
                            track_id=det.track_id,
                            source="opencv",
                            dino_confidence=None,
                            verified=True,
                            entity_id=self._entity_id(obj_type, det.track_id),
                            velocity=det.velocity,
                            attributes=det.attributes,
                        )
                    )
                continue

            # =================================================
            # 2. YOLO (with Motion-Guided High-Res ROI Patching)
            # =================================================

            if self.yolo is not None:
                if self.enable_motion_rois and motion_boxes:
                    yolo_detections = (
                        self.yolo.detect_with_motion_rois(
                            processed_image,
                            motion_boxes=motion_boxes,
                            use_tracking=True,
                        )
                    )
                else:
                    yolo_detections = (
                        self.yolo.track(
                            processed_image
                        )
                    )
            else:
                yolo_detections = []

            # =================================================
            # 2. DINO DISCOVERY
            # =================================================

            dino_detections = []

            run_dino = (
                self.enable_grounding_dino
                and self.dino is not None
                and (
                    frame_index
                    % self.DINO_DISCOVERY_INTERVAL
                    == 0
                )
            )

            if run_dino:

                dino_detections = (
                    self.dino.detect(
                        frame.image,
                        dino_labels,
                    )
                )

            matched_dino_indexes: set[
                int
            ] = set()

            # =================================================
            # 3. YOLO OBJECTS
            # =================================================

            for yolo_detection in yolo_detections:

                object_type = (
                    self._normalise_label(
                        yolo_detection.class_name
                    )
                )

                dino_match = None
                dino_iou = 0.0
                dino_index = None

                if dino_detections:

                    best = None
                    best_iou = 0.0
                    best_index = None

                    for index, dino in enumerate(
                        dino_detections
                    ):

                        if index in matched_dino_indexes:
                            continue

                        dino_label = (
                            self._normalise_label(
                                dino["label"]
                            )
                        )

                        if (
                            dino_label
                            != object_type
                        ):
                            continue

                        current_iou = self._iou(
                            yolo_detection.bbox,
                            dino["bbox"],
                        )

                        if (
                            current_iou
                            > best_iou
                        ):

                            best = dino
                            best_iou = (
                                current_iou
                            )
                            best_index = index

                    if (
                        best is not None
                        and best_iou
                        >= self.DINO_IOU_MATCH_THRESHOLD
                    ):

                        dino_match = best
                        dino_iou = best_iou
                        dino_index = best_index

                if dino_index is not None:
                    matched_dino_indexes.add(
                        dino_index
                    )

                # ---------------------------------------------
                # STRONG YOLO
                # ---------------------------------------------

                if (
                    yolo_detection.confidence
                    >= self.STRONG_YOLO_THRESHOLD
                ):

                    results.append(
                        AIDetectionResult(
                            frame_number=(
                                frame.frame_number
                            ),
                            timestamp_seconds=(
                                frame.timestamp_seconds
                            ),
                            object_type=object_type,
                            confidence=(
                                yolo_detection.confidence
                            ),
                            bbox=yolo_detection.bbox,
                            track_id=(
                                yolo_detection.track_id
                            ),
                            source=(
                                "yolo+dino"
                                if dino_match
                                else "yolo"
                            ),
                            dino_confidence=(
                                dino_match[
                                    "confidence"
                                ]
                                if dino_match
                                else None
                            ),
                            verified=(
                                dino_match
                                is not None
                            ),
                            entity_id=(
                                self._entity_id(
                                    object_type,
                                    yolo_detection.track_id,
                                )
                            ),
                        )
                    )

                    continue

                # ---------------------------------------------
                # DINO CONFIRMS WEAK YOLO
                # ---------------------------------------------

                if dino_match is not None:

                    results.append(
                        AIDetectionResult(
                            frame_number=(
                                frame.frame_number
                            ),
                            timestamp_seconds=(
                                frame.timestamp_seconds
                            ),
                            object_type=object_type,
                            confidence=(
                                yolo_detection.confidence
                            ),
                            bbox=yolo_detection.bbox,
                            track_id=(
                                yolo_detection.track_id
                            ),
                            source="yolo+dino",
                            dino_confidence=(
                                dino_match[
                                    "confidence"
                                ]
                            ),
                            verified=True,
                            entity_id=(
                                self._entity_id(
                                    object_type,
                                    yolo_detection.track_id,
                                )
                            ),
                        )
                    )

            # =================================================
            # 4. DINO-ONLY OBJECTS
            # =================================================

            for index, dino in enumerate(
                dino_detections
            ):

                if index in matched_dino_indexes:
                    continue

                label = self._normalise_label(
                    dino["label"]
                )

                bbox = tuple(
                    float(value)
                    for value in dino["bbox"]
                )

                confidence = float(
                    dino["confidence"]
                )

                # Suppress false positive bicycle detections inside vehicles or persons
                if label in {"bicycle", "motorcycle"}:
                    overlaps_existing = any(
                        r.frame_number == frame.frame_number
                        and r.object_type in {"car", "truck", "bus", "vehicle", "person"}
                        and (self._iou(bbox, r.bbox) > 0.30 or (bbox[0] >= r.bbox[0] and bbox[1] >= r.bbox[1] and bbox[2] <= r.bbox[2] and bbox[3] <= r.bbox[3]))
                        for r in results
                    )
                    if overlaps_existing:
                        continue

                # ---------------------------------------------
                # Give DINO-only objects their own track ID.
                #
                # Negative IDs intentionally distinguish them
                # from YOLO/Ultralytics track IDs.
                # ---------------------------------------------

                track_id = (
                    self._assign_dino_track(
                        label,
                        bbox,
                        frame.frame_number,
                    )
                )

                results.append(
                    AIDetectionResult(
                        frame_number=(
                            frame.frame_number
                        ),
                        timestamp_seconds=(
                            frame.timestamp_seconds
                        ),
                        object_type=label,
                        confidence=confidence,
                        bbox=bbox,
                        track_id=track_id,
                        source="grounding_dino",
                        dino_confidence=confidence,
                        verified=True,
                        entity_id=(
                            self._entity_id(
                                label,
                                track_id,
                            )
                        ),
                    )
                )

        return results