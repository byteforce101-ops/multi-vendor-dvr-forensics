from dataclasses import dataclass
from pathlib import Path
import json
import subprocess


@dataclass
class VideoMetadata:
    path: str
    format_name: str | None
    duration_seconds: float | None
    width: int | None
    height: int | None
    fps: float | None
    frame_count: int | None
    codec: str | None
    pixel_format: str | None
    start_time_seconds: float | None
    has_audio: bool


def _run_ffprobe(video_path: Path) -> dict:
    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_format",
        "-show_streams",
        "-of",
        "json",
        str(video_path),
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=True,
    )

    return json.loads(result.stdout)


def _parse_fps(value: str | None) -> float | None:
    if not value or value in {"0/0", "N/A"}:
        return None

    try:
        if "/" in value:
            numerator, denominator = value.split("/")

            denominator = float(denominator)

            if denominator == 0:
                return None

            return float(numerator) / denominator

        return float(value)

    except (ValueError, ZeroDivisionError):
        return None


def probe_video(video_path: str | Path) -> VideoMetadata:

    video_path = Path(video_path)

    if not video_path.exists():
        raise FileNotFoundError(
            f"Video file does not exist: {video_path}"
        )

    data = _run_ffprobe(video_path)

    streams = data.get("streams", [])

    format_data = data.get("format", {})

    video_stream = next(
        (
            stream
            for stream in streams
            if stream.get("codec_type") == "video"
        ),
        None,
    )

    if video_stream is None:
        raise ValueError(
            f"No video stream found in: {video_path}"
        )

    audio_stream = next(
        (
            stream
            for stream in streams
            if stream.get("codec_type") == "audio"
        ),
        None,
    )

    fps = _parse_fps(
        video_stream.get("avg_frame_rate")
        or video_stream.get("r_frame_rate")
    )

    frame_count = video_stream.get("nb_frames")

    if frame_count is not None:
        try:
            frame_count = int(frame_count)
        except (ValueError, TypeError):
            frame_count = None

    duration = format_data.get("duration")

    if duration is not None:
        try:
            duration = float(duration)
        except (ValueError, TypeError):
            duration = None

    start_time = video_stream.get("start_time")

    if start_time is not None:
        try:
            start_time = float(start_time)
        except (ValueError, TypeError):
            start_time = None

    return VideoMetadata(
        path=str(video_path),
        format_name=format_data.get("format_name"),
        duration_seconds=duration,
        width=video_stream.get("width"),
        height=video_stream.get("height"),
        fps=fps,
        frame_count=frame_count,
        codec=video_stream.get("codec_name"),
        pixel_format=video_stream.get("pix_fmt"),
        start_time_seconds=start_time,
        has_audio=audio_stream is not None,
    )