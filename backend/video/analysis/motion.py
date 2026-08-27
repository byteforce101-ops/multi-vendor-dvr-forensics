from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from backend.video.extraction.frame_extractor import FrameSample


@dataclass
class MotionSample:
    timestamp_seconds: float
    frame_number: int
    score: float
    detected: bool


@dataclass
class MotionEvent:
    start_seconds: float
    end_seconds: float
    peak_score: float


def calculate_motion_score(
    previous: np.ndarray,
    current: np.ndarray,
) -> float:
    previous_gray = cv2.cvtColor(
        previous,
        cv2.COLOR_BGR2GRAY,
    )

    current_gray = cv2.cvtColor(
        current,
        cv2.COLOR_BGR2GRAY,
    )

    previous_gray = cv2.GaussianBlur(
        previous_gray,
        (5, 5),
        0,
    )

    current_gray = cv2.GaussianBlur(
        current_gray,
        (5, 5),
        0,
    )

    difference = cv2.absdiff(
        previous_gray,
        current_gray,
    )

    _, threshold = cv2.threshold(
        difference,
        25,
        255,
        cv2.THRESH_BINARY,
    )

    threshold = cv2.morphologyEx(
        threshold,
        cv2.MORPH_OPEN,
        np.ones((3, 3), np.uint8),
    )

    changed_pixels = np.count_nonzero(threshold)
    total_pixels = threshold.size

    if total_pixels == 0:
        return 0.0

    return changed_pixels / total_pixels


def detect_motion(
    frames: list[FrameSample],
    threshold: float = 0.01,
    min_event_seconds: float = 1.0,
    max_gap_seconds: float = 2.0,
) -> list[MotionEvent]:

    if len(frames) < 2:
        return []

    samples: list[MotionSample] = []

    previous = frames[0]

    for current in frames[1:]:
        score = calculate_motion_score(
            previous.image,
            current.image,
        )

        samples.append(
            MotionSample(
                timestamp_seconds=current.timestamp_seconds,
                frame_number=current.frame_number,
                score=score,
                detected=score >= threshold,
            )
        )

        previous = current

    events: list[MotionEvent] = []

    active_start: float | None = None
    active_end: float | None = None
    peak_score = 0.0

    for sample in samples:

        if sample.detected:
            if active_start is None:
                active_start = sample.timestamp_seconds

            active_end = sample.timestamp_seconds
            peak_score = max(peak_score, sample.score)

        elif active_start is not None:
            assert active_end is not None

            if (
                sample.timestamp_seconds - active_end
                <= max_gap_seconds
            ):
                continue

            if (
                active_end - active_start
                >= min_event_seconds
            ):
                events.append(
                    MotionEvent(
                        start_seconds=active_start,
                        end_seconds=active_end,
                        peak_score=peak_score,
                    )
                )

            active_start = None
            active_end = None
            peak_score = 0.0

    if active_start is not None and active_end is not None:
        if active_end - active_start >= min_event_seconds:
            events.append(
                MotionEvent(
                    start_seconds=active_start,
                    end_seconds=active_end,
                    peak_score=peak_score,
                )
            )

    return events