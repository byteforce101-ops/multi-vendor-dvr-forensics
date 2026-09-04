"""backend/video/playback/ascii_player.py

Forensic ASCII Video Playback Engine.

Converts carved CCTV video streams into high-fidelity Rich ANSI/ASCII text
using dual-pixel half-block Unicode characters ('▀') and true 24-bit color rendering,
enabling real-time video playback directly inside the terminal.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from rich.text import Text

logger = logging.getLogger(__name__)

# ASCII grayscale palette for fallback/monochrome rendering
ASCII_CHARS = " .:-=+*#%@"


class ASCIIFrameConverter:
    """High-performance frame-to-ASCII / ANSI terminal converter."""

    @staticmethod
    def frame_to_half_blocks(
        frame: np.ndarray,
        target_width: int = 76,
        target_height: int = 24,
    ) -> Text:
        """
        Convert a BGR frame into a 24-bit Rich Text using half-blocks ('▀').
        Each terminal row renders 2 vertical image pixels (top=fg, bottom=bg).
        """
        if frame is None or frame.size == 0:
            return Text("No video frame available", style="dim italic red")

        # Double vertical resolution for half-blocks
        img_w = max(10, min(160, target_width))
        img_h = max(6, min(80, target_height * 2))

        resized = cv2.resize(frame, (img_w, img_h), interpolation=cv2.INTER_AREA)
        # Convert BGR to RGB
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)

        text = Text()

        for y in range(0, img_h - 1, 2):
            for x in range(img_w):
                top = rgb[y, x]
                bot = rgb[y + 1, x]
                style = f"rgb({top[0]},{top[1]},{top[2]}) on rgb({bot[0]},{bot[1]},{bot[2]})"
                text.append("▀", style=style)
            text.append("\n")

        return text

    @staticmethod
    def frame_to_ascii_chars(
        frame: np.ndarray,
        target_width: int = 76,
        target_height: int = 24,
    ) -> Text:
        """Convert a BGR frame into ASCII character glyphs based on luminance."""
        if frame is None or frame.size == 0:
            return Text("No video frame available", style="dim italic red")

        img_w = max(10, min(160, target_width))
        img_h = max(6, min(60, target_height))

        resized = cv2.resize(frame, (img_w, img_h), interpolation=cv2.INTER_AREA)
        gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)

        text = Text()
        num_chars = len(ASCII_CHARS)

        for y in range(img_h):
            for x in range(img_w):
                lum = gray[y, x]
                char_idx = int(lum / 256.0 * num_chars)
                char_idx = min(num_chars - 1, max(0, char_idx))
                ch = ASCII_CHARS[char_idx]

                pixel = rgb[y, x]
                style = f"rgb({pixel[0]},{pixel[1]},{pixel[2]})"
                text.append(ch, style=style)
            text.append("\n")

        return text


class VideoPlaybackSession:
    """Manages playback position, frame decoding, and seek operations for an evidence video."""

    def __init__(self, video_path: str | Path):
        self.video_path = Path(video_path)
        self.cap: Optional[cv2.VideoCapture] = None
        self.total_frames: int = 0
        self.fps: float = 25.0
        self.duration_seconds: float = 0.0
        self.current_frame_idx: int = 0
        self.is_playing: bool = False
        self.playback_speed: float = 1.0
        self.color_mode: str = "half_blocks"  # "half_blocks" | "ascii"
        self._cached_frame: Optional[np.ndarray] = None

        self._open()

    def _open(self) -> None:
        """Open the video stream and read metadata."""
        if not self.video_path.exists():
            return

        self.cap = cv2.VideoCapture(str(self.video_path))
        if self.cap.isOpened():
            self.total_frames = max(1, int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT)))
            fps_val = self.cap.get(cv2.CAP_PROP_FPS)
            self.fps = fps_val if fps_val and fps_val > 0.0 else 25.0
            self.duration_seconds = self.total_frames / self.fps
            self.read_frame(0)

    def close(self) -> None:
        """Release video capture resources."""
        if self.cap is not None:
            self.cap.release()
            self.cap = None

    def read_frame(self, frame_idx: int) -> Optional[np.ndarray]:
        """Seek and read a specific frame."""
        if self.cap is None or not self.cap.isOpened():
            return None

        frame_idx = max(0, min(self.total_frames - 1, frame_idx))
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = self.cap.read()
        if ret and frame is not None:
            self.current_frame_idx = frame_idx
            self._cached_frame = frame
            return frame
        return self._cached_frame

    def next_frame(self) -> Optional[np.ndarray]:
        """Advance by 1 frame or loop."""
        next_idx = self.current_frame_idx + 1
        if next_idx >= self.total_frames:
            next_idx = 0  # loop playback
        return self.read_frame(next_idx)

    def prev_frame(self) -> Optional[np.ndarray]:
        """Step back by 1 frame."""
        prev_idx = max(0, self.current_frame_idx - 1)
        return self.read_frame(prev_idx)

    def seek_percent(self, pct: float) -> Optional[np.ndarray]:
        """Seek to a relative percentage (0.0 - 1.0)."""
        idx = int(pct * max(1, self.total_frames - 1))
        return self.read_frame(idx)

    def render_current_ascii(
        self,
        width: int = 76,
        height: int = 22,
    ) -> Text:
        """Render the current frame as rich ANSI half-blocks or ASCII glyphs."""
        if self._cached_frame is None:
            self.read_frame(self.current_frame_idx)

        if self._cached_frame is None:
            return Text(
                f"[Video unavailable: {self.video_path.name}]",
                style="dim yellow italic",
            )

        if self.color_mode == "half_blocks":
            return ASCIIFrameConverter.frame_to_half_blocks(
                self._cached_frame,
                target_width=width,
                target_height=height,
            )
        else:
            return ASCIIFrameConverter.frame_to_ascii_chars(
                self._cached_frame,
                target_width=width,
                target_height=height,
            )

    def get_status_line(self) -> str:
        """Format the playback progress and metadata string."""
        cur_ts = self.current_frame_idx / max(0.1, self.fps)
        cur_ts_str = f"{int(cur_ts // 60):02d}:{cur_ts % 60:04.1f}"
        tot_ts_str = f"{int(self.duration_seconds // 60):02d}:{self.duration_seconds % 60:04.1f}"
        state_tag = "▶ PLAYING" if self.is_playing else "⏸ PAUSED"
        return (
            f"[{state_tag}] Frame: {self.current_frame_idx + 1}/{self.total_frames} "
            f"({cur_ts_str} / {tot_ts_str}) • {self.fps:.1f} FPS • {self.playback_speed:.1f}x • Mode: {self.color_mode.upper()}"
        )
