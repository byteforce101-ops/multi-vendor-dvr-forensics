from __future__ import annotations

from dataclasses import dataclass, field
from math import hypot


@dataclass
class EntityObservation:
    frame_number: int
    timestamp_seconds: float

    bbox: tuple[
        float,
        float,
        float,
        float,
    ]

    confidence: float

    sources: list[str] = field(
        default_factory=list
    )


@dataclass
class Entity:

    entity_id: str

    object_type: str

    first_seen_frame: int
    first_seen_seconds: float

    last_seen_frame: int
    last_seen_seconds: float

    bbox: tuple[
        float,
        float,
        float,
        float,
    ]

    confidence: float

    detector_track_id: int | None = None

    observations: list[
        EntityObservation
    ] = field(
        default_factory=list
    )

    missed_frames: int = 0

    active: bool = True


class EntityTracker:

    def __init__(
        self,
        max_missed_frames: int = 3,
        iou_threshold: float = 0.20,
        distance_threshold: float = 180.0,
    ):

        self.max_missed_frames = (
            max_missed_frames
        )

        self.iou_threshold = (
            iou_threshold
        )

        self.distance_threshold = (
            distance_threshold
        )

        self.entities: dict[
            str,
            Entity,
        ] = {}

        self.next_entity_number = 1

    def reset(self):

        self.entities.clear()

        self.next_entity_number = 1

    @staticmethod
    def _iou(a, b) -> float:

        ax1, ay1, ax2, ay2 = a
        bx1, by1, bx2, by2 = b

        ix1 = max(ax1, bx1)
        iy1 = max(ay1, by1)
        ix2 = min(ax2, bx2)
        iy2 = min(ay2, by2)

        iw = max(
            0.0,
            ix2 - ix1,
        )

        ih = max(
            0.0,
            iy2 - iy1,
        )

        intersection = iw * ih

        if intersection <= 0:
            return 0.0

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

    @staticmethod
    def _center(box):

        x1, y1, x2, y2 = box

        return (
            (x1 + x2) / 2.0,
            (y1 + y2) / 2.0,
        )

    def _distance(
        self,
        a,
        b,
    ) -> float:

        ax, ay = self._center(a)
        bx, by = self._center(b)

        return hypot(
            ax - bx,
            ay - by,
        )

    def _new_entity(
        self,
        detection,
        frame_number: int,
        timestamp_seconds: float,
    ) -> Entity:

        entity_id = (
            f"entity_{self.next_entity_number}"
        )

        self.next_entity_number += 1

        observation = (
            EntityObservation(
                frame_number=frame_number,
                timestamp_seconds=(
                    timestamp_seconds
                ),
                bbox=detection.bbox,
                confidence=(
                    detection.confidence
                ),
                sources=list(
                    detection.sources
                ),
            )
        )

        entity = Entity(
            entity_id=entity_id,
            object_type=(
                detection.object_type
            ),
            first_seen_frame=frame_number,
            first_seen_seconds=(
                timestamp_seconds
            ),
            last_seen_frame=frame_number,
            last_seen_seconds=(
                timestamp_seconds
            ),
            bbox=detection.bbox,
            confidence=(
                detection.confidence
            ),
            detector_track_id=(
                detection.track_id
            ),
            observations=[
                observation
            ],
        )

        self.entities[
            entity_id
        ] = entity

        return entity

    def update(
        self,
        detections,
        frame_number: int,
        timestamp_seconds: float,
    ):

        active_entities = [
            entity
            for entity
            in self.entities.values()
            if entity.active
        ]

        assignments = {}

        used_entities = set()

        # --------------------------------------------------
        # First preference: detector track ID
        # --------------------------------------------------

        for index, detection in enumerate(
            detections
        ):

            if detection.track_id is None:
                continue

            best_entity = None

            for entity in active_entities:

                if entity.entity_id in used_entities:
                    continue

                if (
                    entity.object_type
                    != detection.object_type
                ):
                    continue

                if (
                    entity.detector_track_id
                    != detection.track_id
                ):
                    continue

                best_entity = entity
                break

            if best_entity is not None:

                assignments[
                    index
                ] = best_entity

                used_entities.add(
                    best_entity.entity_id
                )

        # --------------------------------------------------
        # Second preference: spatial matching
        # --------------------------------------------------

        for index, detection in enumerate(
            detections
        ):

            if index in assignments:
                continue

            best_entity = None
            best_score = -1.0

            for entity in active_entities:

                if (
                    entity.entity_id
                    in used_entities
                ):
                    continue

                if (
                    entity.object_type
                    != detection.object_type
                ):
                    continue

                iou = self._iou(
                    entity.bbox,
                    detection.bbox,
                )

                distance = self._distance(
                    entity.bbox,
                    detection.bbox,
                )

                if (
                    iou
                    < self.iou_threshold
                    and distance
                    > self.distance_threshold
                ):
                    continue

                distance_score = max(
                    0.0,
                    1.0
                    - (
                        distance
                        / self.distance_threshold
                    ),
                )

                score = (
                    iou * 0.65
                    + distance_score * 0.35
                )

                if score > best_score:
                    best_score = score
                    best_entity = entity

            if best_entity is not None:

                assignments[
                    index
                ] = best_entity

                used_entities.add(
                    best_entity.entity_id
                )

        # --------------------------------------------------
        # Mark active entities as missed
        # --------------------------------------------------

        for entity in active_entities:

            if (
                entity.entity_id
                not in used_entities
            ):

                entity.missed_frames += 1

                if (
                    entity.missed_frames
                    > self.max_missed_frames
                ):
                    entity.active = False

        # --------------------------------------------------
        # Apply detections
        # --------------------------------------------------

        output = []

        for index, detection in enumerate(
            detections
        ):

            entity = assignments.get(
                index
            )

            if entity is None:

                entity = self._new_entity(
                    detection,
                    frame_number,
                    timestamp_seconds,
                )

            else:

                entity.bbox = (
                    detection.bbox
                )

                entity.confidence = max(
                    entity.confidence,
                    detection.confidence,
                )

                entity.last_seen_frame = (
                    frame_number
                )

                entity.last_seen_seconds = (
                    timestamp_seconds
                )

                entity.detector_track_id = (
                    detection.track_id
                )

                entity.missed_frames = 0
                entity.active = True

                entity.observations.append(
                    EntityObservation(
                        frame_number=frame_number,
                        timestamp_seconds=(
                            timestamp_seconds
                        ),
                        bbox=detection.bbox,
                        confidence=(
                            detection.confidence
                        ),
                        sources=list(
                            detection.sources
                        ),
                    )
                )

            output.append(
                (
                    detection,
                    entity,
                )
            )

        return output

    def finalize(self):

        for entity in self.entities.values():
            entity.active = False

        return list(
            self.entities.values()
        )