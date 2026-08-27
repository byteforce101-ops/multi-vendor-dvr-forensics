from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import av
import numpy as np


@dataclass
class FrameSample:
    frame_number: int
    timestamp_seconds: float
    image: np.ndarray


def iter_frames(
    video_path: str | Path,
    sample_fps: float | None = None,
) -> Iterator[FrameSample]:

    video_path = Path(video_path)

    if not video_path.exists():
        raise FileNotFoundError(
            f"Video file does not exist: {video_path}"
        )

    container = av.open(str(video_path))

    try:
        stream = container.streams.video[0]

        original_fps = float(stream.average_rate or 0)

        if original_fps <= 0:
            original_fps = 30.0

        interval = None

        if sample_fps is not None:
            if sample_fps <= 0:
                raise ValueError(
                    "sample_fps must be greater than 0"
                )

            interval = 1.0 / sample_fps

        next_sample_time = 0.0
        frame_number = 0

        for frame in container.decode(stream):

            if frame.pts is not None:
                timestamp = float(
                    frame.pts * stream.time_base
                )
            else:
                timestamp = frame_number / original_fps

            if (
                interval is not None
                and timestamp < next_sample_time
            ):
                frame_number += 1
                continue

            image = frame.to_ndarray(
                format="bgr24"
            )

            yield FrameSample(
                frame_number=frame_number,
                timestamp_seconds=timestamp,
                image=image,
            )

            if interval is not None:
                next_sample_time = (
                    timestamp + interval
                )

            frame_number += 1

    finally:
        container.close()