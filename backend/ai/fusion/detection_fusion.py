from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class FusedDetection:
    object_type: str

    confidence: float

    bbox: tuple[
        float,
        float,
        float,
        float,
    ]

    track_id: int | None = None

    sources: list[str] = field(
        default_factory=list
    )

    model_confidences: dict[
        str,
        float
    ] = field(
        default_factory=dict
    )

    verified: bool = False


def box_iou(
    a,
    b,
) -> float:

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

    intersection = (
        iw * ih
    )

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

    return (
        intersection / union
    )


def fuse_detections(
    candidates: list[dict],
    iou_threshold: float = 0.45,
) -> list[FusedDetection]:

    ordered = sorted(
        candidates,
        key=lambda item: item[
            "confidence"
        ],
        reverse=True,
    )

    fused: list[
        FusedDetection
    ] = []

    for candidate in ordered:

        label = str(
            candidate[
                "object_type"
            ]
        ).strip().lower()

        bbox = tuple(
            float(value)
            for value
            in candidate["bbox"]
        )

        confidence = float(
            candidate["confidence"]
        )

        source = str(
            candidate.get(
                "source",
                "unknown",
            )
        )

        matched = None

        for existing in fused:

            if (
                existing.object_type
                != label
            ):
                continue

            if (
                box_iou(
                    existing.bbox,
                    bbox,
                )
                >= iou_threshold
            ):
                matched = existing
                break

        if matched is None:

            fused.append(
                FusedDetection(
                    object_type=label,
                    confidence=confidence,
                    bbox=bbox,
                    track_id=candidate.get(
                        "track_id"
                    ),
                    sources=[source],
                    model_confidences={
                        source: confidence
                    },
                    verified=False,
                )
            )

            continue

        matched.sources.append(
            source
        )

        matched.model_confidences[
            source
        ] = confidence

        # Keep the highest-confidence box.
        if (
            confidence
            > matched.confidence
        ):
            matched.confidence = (
                confidence
            )
            matched.bbox = bbox

        if (
            matched.track_id is None
            and candidate.get(
                "track_id"
            )
            is not None
        ):
            matched.track_id = (
                candidate.get(
                    "track_id"
                )
            )

    for item in fused:

        item.sources = list(
            dict.fromkeys(
                item.sources
            )
        )

        # Independent model agreement is strong
        # evidence, even if individual confidence
        # values are modest.
        item.verified = (
            len(item.sources) >= 2
        )

        if item.verified:
            best = max(
                item.model_confidences.values()
            )

            agreement_bonus = min(
                0.15,
                0.05
                * (
                    len(
                        item.sources
                    )
                    - 1
                ),
            )

            item.confidence = min(
                1.0,
                best
                + agreement_bonus,
            )

    return fused