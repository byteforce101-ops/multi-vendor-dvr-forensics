"""backend/video/playback/ascii_player.py

Forensic ASCII/ANSI Video Playback Engine.

Converts carved CCTV video streams into high-fidelity Rich ANSI/ASCII text
using dual-pixel half-block Unicode characters ('▀') and 24-bit TrueColor rendering,
enabling smooth, high-resolution full-width video playback directly inside the terminal.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from rich.text import Text

from backend.video.enhancement.preprocessor import enhance_surveillance_frame

logger = logging.getLogger(__name__)

# ASCII grayscale palette for fallback/monochrome rendering
ASCII_CHARS = " .:-=+*#%@"

# Available playback visualization modes
PLAYBACK_MODES = ["half_blocks", "enhanced", "high_contrast", "braille", "ascii"]


class ASCIIFrameConverter:
    """High-performance frame-to-ASCII / ANSI terminal converter."""

    @staticmethod
    def frame_to_half_blocks(
        frame: np.ndarray,
        target_width: int = 76,
        target_height: int = 24,
        enhance: bool = False,
    ) -> Text:
        """
        Convert a BGR frame into a 24-bit Rich Text using half-blocks ('▀').
        Each terminal row renders 2 vertical image pixels (top=fg, bottom=bg),
        maximizing terminal panel resolution.
        """
        if frame is None or frame.size == 0:
            return Text("No video frame available", style="dim italic red")

        # Full-width viewport scaling matching the panel width for maximum detail
        img_w = max(10, min(160, target_width))
        img_h = max(6, min(80, target_height * 2))
        img_h = (img_h // 2) * 2

        proc_frame = frame
        if enhance:
            proc_frame = enhance_surveillance_frame(
                frame,
                enable_clahe=True,
                auto_gamma=True,
                enable_sharpen=False,
                clahe_clip_limit=2.0,
            )

        resized = cv2.resize(proc_frame, (img_w, img_h), interpolation=cv2.INTER_AREA)

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
    def frame_to_high_contrast(
        frame: np.ndarray,
        target_width: int = 76,
        target_height: int = 24,
    ) -> Text:
        """High-contrast forensic surveillance rendering for dark, low-light footage."""
        if frame is None or frame.size == 0:
            return Text("No video frame available", style="dim italic red")

        img_w = max(10, min(160, target_width))
        img_h = max(6, min(80, target_height * 2))
        img_h = (img_h // 2) * 2

        enhanced = enhance_surveillance_frame(
            frame,
            enable_clahe=True,
            auto_gamma=True,
            enable_sharpen=True,
            clahe_clip_limit=3.0,
            sharpen_strength=0.8,
        )

        resized = cv2.resize(enhanced, (img_w, img_h), interpolation=cv2.INTER_AREA)
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)

        text = Text()
        for y in range(0, img_h - 1, 2):
            for x in range(img_w):
                top = rgb[y, x]
                bot = rgb[y + 1, x]
                style = f"bold rgb({top[0]},{top[1]},{top[2]}) on rgb({bot[0]},{bot[1]},{bot[2]})"
                text.append("▀", style=style)
            text.append("\n")

        return text

    @staticmethod
    def frame_to_braille(
        frame: np.ndarray,
        target_width: int = 76,
        target_height: int = 24,
    ) -> Text:
        """
        Convert frame into ultra-high-resolution 2x4 subpixel Unicode Braille characters.
        Provides 2x horizontal and 4x vertical subpixel resolution for fine contours.
        """
        if frame is None or frame.size == 0:
            return Text("No video frame available", style="dim italic red")

        sub_w = max(20, min(240, target_width * 2))
        sub_h = max(12, min(160, target_height * 4))
        sub_w = (sub_w // 2) * 2
        sub_h = (sub_h // 4) * 4

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        resized_gray = cv2.resize(gray, (sub_w, sub_h), interpolation=cv2.INTER_AREA)

        binary = cv2.adaptiveThreshold(
            resized_gray,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            9,
            2,
        )

        text = Text()
        braille_base = 0x2800

        for y in range(0, sub_h, 4):
            for x in range(0, sub_w, 2):
                byte_val = 0
                if binary[y + 0, x + 0] > 128: byte_val |= 0x01
                if binary[y + 1, x + 0] > 128: byte_val |= 0x02
                if binary[y + 2, x + 0] > 128: byte_val |= 0x04
                if binary[y + 3, x + 0] > 128: byte_val |= 0x40

                if binary[y + 0, x + 1] > 128: byte_val |= 0x08
                if binary[y + 1, x + 1] > 128: byte_val |= 0x10
                if binary[y + 2, x + 1] > 128: byte_val |= 0x20
                if binary[y + 3, x + 1] > 128: byte_val |= 0x80

                char = chr(braille_base + byte_val)
                text.append(char, style="bright_cyan")
            text.append("\n")

        return text

    @staticmethod
    def frame_to_ascii_chars(
        frame: np.ndarray,
        target_width: int = 76,
        target_height: int = 24,
        enhance: bool = False,
    ) -> Text:
        """Convert a BGR frame into ASCII character glyphs based on luminance."""
        if frame is None or frame.size == 0:
            return Text("No video frame available", style="dim italic red")

        img_w = max(10, min(160, target_width))
        img_h = max(6, min(60, target_height))

        proc = frame
        if enhance:
            proc = enhance_surveillance_frame(
                frame, enable_clahe=True, auto_gamma=True, enable_sharpen=False
            )

        resized = cv2.resize(proc, (img_w, img_h), interpolation=cv2.INTER_AREA)
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
        self.playback_speed: float = 1.25
        self.color_mode: str = "half_blocks"  # default to clean TrueColor half-blocks
        self.enhance_enabled: bool = False
        self._cap_pos: int = -1
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
        """Read frame, seeking only if non-consecutive for high-speed playback."""
        if self.cap is None or not self.cap.isOpened():
            return None

        frame_idx = max(0, min(self.total_frames - 1, frame_idx))
        if self._cap_pos != frame_idx:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            self._cap_pos = frame_idx

        ret, frame = self.cap.read()
        if ret and frame is not None:
            self.current_frame_idx = frame_idx
            self._cap_pos = frame_idx + 1
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

    def toggle_enhancement(self) -> bool:
        """Toggle forensic enhancement on or off."""
        self.enhance_enabled = not self.enhance_enabled
        return self.enhance_enabled

    def cycle_mode(self) -> str:
        """Cycle through available video playback rendering modes."""
        curr_idx = PLAYBACK_MODES.index(self.color_mode) if self.color_mode in PLAYBACK_MODES else 0
        next_idx = (curr_idx + 1) % len(PLAYBACK_MODES)
        self.color_mode = PLAYBACK_MODES[next_idx]
        return self.color_mode

    def render_current_ascii(
        self,
        width: int = 76,
        height: int = 22,
    ) -> Text:
        """Render the current frame across the panel width for maximum clarity."""
        if self._cached_frame is None:
            self.read_frame(self.current_frame_idx)

        if self._cached_frame is None:
            return Text(
                f"[Video unavailable: {self.video_path.name}]",
                style="dim yellow italic",
            )

        mode = self.color_mode.lower()
        if mode == "enhanced":
            return ASCIIFrameConverter.frame_to_half_blocks(
                self._cached_frame,
                target_width=width,
                target_height=height,
                enhance=True,
            )
        elif mode == "high_contrast":
            return ASCIIFrameConverter.frame_to_high_contrast(
                self._cached_frame,
                target_width=width,
                target_height=height,
            )
        elif mode == "braille":
            return ASCIIFrameConverter.frame_to_braille(
                self._cached_frame,
                target_width=width,
                target_height=height,
            )
        elif mode == "ascii":
            return ASCIIFrameConverter.frame_to_ascii_chars(
                self._cached_frame,
                target_width=width,
                target_height=height,
                enhance=self.enhance_enabled,
            )
        else:  # "half_blocks"
            return ASCIIFrameConverter.frame_to_half_blocks(
                self._cached_frame,
                target_width=width,
                target_height=height,
                enhance=self.enhance_enabled,
            )

    def get_status_line(self) -> str:
        """Format the playback progress, mode, and enhancement status string."""
        cur_ts = self.current_frame_idx / max(0.1, self.fps)
        cur_ts_str = f"{int(cur_ts // 60):02d}:{cur_ts % 60:04.1f}"
        tot_ts_str = f"{int(self.duration_seconds // 60):02d}:{self.duration_seconds % 60:04.1f}"
        state_tag = "▶ PLAYING" if self.is_playing else "⏸ PAUSED"
        enh_tag = "ON" if self.enhance_enabled else "OFF"
        return (
            f"[{state_tag}] Frame: {self.current_frame_idx + 1}/{self.total_frames} "
            f"({cur_ts_str} / {tot_ts_str}) • {self.fps:.1f} FPS • Mode: {self.color_mode.upper()} • Enhance: {enh_tag}"
        )

