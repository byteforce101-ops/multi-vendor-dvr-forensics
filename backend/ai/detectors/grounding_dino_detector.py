from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import torch
from PIL import Image
from transformers import (
    AutoModelForZeroShotObjectDetection,
    AutoProcessor,
)


class GroundingDINODetector:

    def __init__(
        self,
        model_name: str = "IDEA-Research/grounding-dino-base",
        confidence: float = 0.20,
        text_confidence: float = 0.20,
        device: str | None = None,
        label_chunk_size: int = 8,
        dedup_iou: float = 0.70,
    ):
        self.device = device or (
            "cuda" if torch.cuda.is_available() else "cpu"
        )

        self.confidence = confidence
        self.text_confidence = text_confidence

        # IMPORTANT:
        # Grounding DINO should not receive hundreds of labels
        # in a single text query.
        self.label_chunk_size = max(
            1,
            int(label_chunk_size),
        )

        self.dedup_iou = float(dedup_iou)

        self.processor = AutoProcessor.from_pretrained(
            model_name
        )

        self.model = (
            AutoModelForZeroShotObjectDetection
            .from_pretrained(model_name)
            .to(self.device)
        )

        self.model.eval()

    # ------------------------------------------------------------------
    # IMAGE CONVERSION
    # ------------------------------------------------------------------

    def _to_pil(self, image) -> Image.Image:

        if isinstance(image, (str, Path)):
            return Image.open(image).convert("RGB")

        if isinstance(image, Image.Image):
            return image.convert("RGB")

        if isinstance(image, np.ndarray):

            if image.ndim != 3:
                raise ValueError(
                    "Expected a color image with 3 dimensions."
                )

            rgb = cv2.cvtColor(
                image,
                cv2.COLOR_BGR2RGB,
            )

            return Image.fromarray(rgb)

        raise TypeError(
            f"Unsupported image type: {type(image)}"
        )

    # ------------------------------------------------------------------
    # PUBLIC DETECTION
    # ------------------------------------------------------------------

    def detect(
        self,
        image,
        labels: list[str],
    ) -> list[dict]:

        pil_image = self._to_pil(image)

        # Clean labels.
        cleaned_labels = []

        seen_labels = set()

        for label in labels:

            if not isinstance(label, str):
                continue

            label = label.strip().lower()

            if not label:
                continue

            if label in seen_labels:
                continue

            seen_labels.add(label)

            cleaned_labels.append(label)

        if not cleaned_labels:
            return []

        # --------------------------------------------------------------
        # IMPORTANT FIX
        #
        # Never send the entire vocabulary to Grounding DINO.
        # Process small groups instead.
        # --------------------------------------------------------------

        all_detections: list[dict] = []

        for start in range(
            0,
            len(cleaned_labels),
            self.label_chunk_size,
        ):

            chunk = cleaned_labels[
                start:start + self.label_chunk_size
            ]

            try:

                chunk_detections = self._detect_chunk(
                    pil_image,
                    chunk,
                )

                all_detections.extend(
                    chunk_detections
                )

            except Exception as exc:

                # A failed DINO query must NEVER destroy
                # the complete YOLO analysis.
                print(
                    "[GroundingDINO] "
                    f"Skipping label group {chunk}: {exc}"
                )

                continue

        # Remove duplicates caused by overlapping
        # vocabulary groups.
        return self._deduplicate(
            all_detections
        )

    # ------------------------------------------------------------------
    # SINGLE CHUNK
    # ------------------------------------------------------------------

    def _detect_chunk(
        self,
        pil_image: Image.Image,
        labels: list[str],
    ) -> list[dict]:

        # Grounding DINO works reliably with short
        # natural-language queries.
        #
        # The official examples use formats such as:
        # "a cat. a remote control."
        #
        # We create one prompt containing the small
        # label group.
        text = ". ".join(
            f"a {label}"
            for label in labels
        ) + "."

        inputs = self.processor(
            images=pil_image,
            text=text,
            return_tensors="pt",
        )

        # Move tensors to CPU/GPU.
        inputs = {
            key: value.to(self.device)
            if hasattr(value, "to")
            else value
            for key, value in inputs.items()
        }

        with torch.inference_mode():

            outputs = self.model(
                **inputs
            )

        results = (
            self.processor
            .post_process_grounded_object_detection(
                outputs,
                inputs.input_ids,
                threshold=self.confidence,
                text_threshold=self.text_confidence,
                target_sizes=[
                    (
                        pil_image.height,
                        pil_image.width,
                    )
                ],
            )[0]
        )

        boxes = results.get(
            "boxes",
            []
        )

        scores = results.get(
            "scores",
            []
        )

        # Current Transformers versions normally expose
        # "text_labels".
        labels_result = results.get(
            "text_labels",
            results.get(
                "labels",
                [],
            ),
        )

        detections = []

        for box, score, label in zip(
            boxes,
            scores,
            labels_result,
        ):

            confidence = float(
                score.item()
                if hasattr(score, "item")
                else score
            )

            label = str(
                label
            ).lower().strip()

            if not label:
                continue

            # Grounding DINO can sometimes return
            # punctuation or article prefixes.
            label = self._clean_label(
                label
            )

            if not label:
                continue

            bbox = [
                float(value)
                for value in box.tolist()
            ]

            detections.append(
                {
                    "label": label,
                    "confidence": confidence,
                    "bbox": bbox,
                }
            )

        return detections

    # ------------------------------------------------------------------
    # LABEL CLEANING
    # ------------------------------------------------------------------

    @staticmethod
    def _clean_label(
        label: str,
    ) -> str:

        label = label.lower().strip()

        prefixes = (
            "a ",
            "an ",
            "the ",
        )

        for prefix in prefixes:

            if label.startswith(prefix):

                label = label[
                    len(prefix):
                ].strip()

                break

        # Grounding DINO may return punctuation.
        label = label.strip(
            " .,!?:;\"'"
        )

        return label

    # ------------------------------------------------------------------
    # IOU
    # ------------------------------------------------------------------

    @staticmethod
    def _iou(
        box_a: list[float],
        box_b: list[float],
    ) -> float:

        ax1, ay1, ax2, ay2 = box_a
        bx1, by1, bx2, by2 = box_b

        ix1 = max(
            ax1,
            bx1,
        )

        iy1 = max(
            ay1,
            by1,
        )

        ix2 = min(
            ax2,
            bx2,
        )

        iy2 = min(
            ay2,
            by2,
        )

        intersection_width = max(
            0.0,
            ix2 - ix1,
        )

        intersection_height = max(
            0.0,
            iy2 - iy1,
        )

        intersection = (
            intersection_width
            * intersection_height
        )

        area_a = max(
            0.0,
            ax2 - ax1,
        ) * max(
            0.0,
            ay2 - ay1,
        )

        area_b = max(
            0.0,
            bx2 - bx1,
        ) * max(
            0.0,
            by2 - by1,
        )

        union = (
            area_a
            + area_b
            - intersection
        )

        if union <= 0:
            return 0.0

        return intersection / union

    # ------------------------------------------------------------------
    # DUPLICATE REMOVAL
    # ------------------------------------------------------------------

    def _deduplicate(
        self,
        detections: list[dict],
    ) -> list[dict]:

        if not detections:
            return []

        # Highest-confidence detections first.
        ordered = sorted(
            detections,
            key=lambda item: item["confidence"],
            reverse=True,
        )

        kept: list[dict] = []

        for detection in ordered:

            duplicate = False

            for existing in kept:

                # Only compare detections that refer
                # to the same semantic object class.
                if (
                    detection["label"]
                    != existing["label"]
                ):
                    continue

                iou = self._iou(
                    detection["bbox"],
                    existing["bbox"],
                )

                if iou >= self.dedup_iou:

                    duplicate = True
                    break

            if not duplicate:
                kept.append(
                    detection
                )

        return kept