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


class DVRScanMotionDetector:
    """OpenCV MOG2 background-subtraction motion detector inspired by Breakthrough/DVR-Scan."""

    def __init__(
        self,
        history: int = 500,
        var_threshold: float = 16.0,
        detect_shadows: bool = False,
        downscale_factor: int = 1,
        morph_kernel_size: int = 3,
    ):
        self.subtractor = cv2.createBackgroundSubtractorMOG2(
            history=history,
            varThreshold=var_threshold,
            detectShadows=detect_shadows,
        )
        self.downscale_factor = max(1, int(downscale_factor))
        self.kernel = np.ones((morph_kernel_size, morph_kernel_size), np.uint8)

    def process_frame(self, frame: np.ndarray, roi: tuple[int, int, int, int] | None = None) -> tuple[float, list[tuple[int, int, int, int]]]:
        """Apply MOG2 background subtraction, morphology, and contour bounding box extraction.
        Returns (motion_score: float, bounding_boxes: list[(x, y, w, h)]).
        """
        if roi is not None:
            rx, ry, rw, rh = roi
            frame = frame[ry:ry + rh, rx:rx + rw]

        h, w = frame.shape[:2]
        if self.downscale_factor > 1:
            frame = cv2.resize(
                frame,
                (w // self.downscale_factor, h // self.downscale_factor),
                interpolation=cv2.INTER_AREA,
            )

        fg_mask = self.subtractor.apply(frame)
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, self.kernel)
        fg_mask = cv2.dilate(fg_mask, self.kernel, iterations=1)

        total_pixels = fg_mask.size
        if total_pixels == 0:
            return 0.0, []

        changed_pixels = np.count_nonzero(fg_mask)
        score = changed_pixels / total_pixels

        contours, _ = cv2.findContours(fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        boxes = []
        for c in contours:
            if cv2.contourArea(c) > 50:
                bx, by, bw, bh = cv2.boundingRect(c)
                if self.downscale_factor > 1:
                    bx *= self.downscale_factor
                    by *= self.downscale_factor
                    bw *= self.downscale_factor
                    bh *= self.downscale_factor
                if roi is not None:
                    bx += rx
                    by += ry
                boxes.append((bx, by, bw, bh))

        return score, boxes


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
    use_mog2: bool = True,
) -> list[MotionEvent]:

    if len(frames) < 2:
        return []

    samples: list[MotionSample] = []

    if use_mog2:
        detector = DVRScanMotionDetector()
        for frame_sample in frames:
            score, _ = detector.process_frame(frame_sample.image)
            samples.append(
                MotionSample(
                    timestamp_seconds=frame_sample.timestamp_seconds,
                    frame_number=frame_sample.frame_number,
                    score=score,
                    detected=score >= threshold,
                )
            )
    else:
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