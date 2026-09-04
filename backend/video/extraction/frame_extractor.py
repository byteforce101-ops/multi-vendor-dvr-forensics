from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import cv2
import numpy as np

try:
    import av
except ImportError:
    av = None


@dataclass
class FrameSample:
    frame_number: int
    timestamp_seconds: float
    image: np.ndarray


def iter_frames(
    video_path: str | Path,
    sample_fps: float | None = None,
) -> Iterator[FrameSample]:
    """Iterate sampled frames using OpenCV VideoCapture with fallback to PyAV."""
    video_path = Path(video_path)

    if not video_path.exists():
        raise FileNotFoundError(
            f"Video file does not exist: {video_path}"
        )

    # 1. Primary decoder: OpenCV VideoCapture (robust, fast, matches DVR-Scan)
    cap = cv2.VideoCapture(str(video_path))
    if cap.isOpened():
        try:
            fps = float(cap.get(cv2.CAP_PROP_FPS) or 0)
            if fps <= 0 or np.isnan(fps):
                fps = 30.0

            interval = (1.0 / sample_fps) if (sample_fps and sample_fps > 0) else None
            next_sample_time = 0.0
            frame_number = 0

            while True:
                ret, frame = cap.read()
                if not ret or frame is None:
                    break

                pos_msec = cap.get(cv2.CAP_PROP_POS_MSEC)
                if pos_msec > 0:
                    timestamp = pos_msec / 1000.0
                else:
                    timestamp = frame_number / fps

                if interval is not None and timestamp < next_sample_time and frame_number > 0:
                    frame_number += 1
                    continue

                yield FrameSample(
                    frame_number=frame_number,
                    timestamp_seconds=timestamp,
                    image=frame,
                )

                if interval is not None:
                    next_sample_time = timestamp + interval

                frame_number += 1

            if frame_number > 0:
                return
        finally:
            cap.release()

    # 2. Fallback decoder: PyAV
    if av is not None:
        container = av.open(str(video_path))
        try:
            stream = container.streams.video[0]
            original_fps = float(stream.average_rate or 0)
            if original_fps <= 0:
                original_fps = 30.0

            interval = (1.0 / sample_fps) if (sample_fps and sample_fps > 0) else None
            next_sample_time = 0.0
            frame_number = 0

            try:
                for frame in container.decode(stream):
                    if frame.pts is not None:
                        timestamp = float(frame.pts * stream.time_base)
                    else:
                        timestamp = frame_number / original_fps

                    if interval is not None and timestamp < next_sample_time and frame_number > 0:
                        frame_number += 1
                        continue

                    image = frame.to_ndarray(format="bgr24")
                    yield FrameSample(
                        frame_number=frame_number,
                        timestamp_seconds=timestamp,
                        image=image,
                    )

                    if interval is not None:
                        next_sample_time = timestamp + interval

                    frame_number += 1
            except Exception:
                # Trailing packet decode errors are common at end of streams
                pass
        finally:
            container.close()