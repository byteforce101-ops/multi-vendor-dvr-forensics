"""Unit tests for ASCII video player and terminal frame conversion."""

import numpy as np
import pytest

from backend.video.playback.ascii_player import (
    ASCIIFrameConverter,
    VideoPlaybackSession,
)


def test_ascii_frame_converter_half_blocks():
    """Verify half-block TrueColor terminal text conversion."""
    # Create a 64x64 synthetic BGR test image
    frame = np.zeros((64, 64, 3), dtype=np.uint8)
    frame[:32, :] = [255, 0, 0]    # Blue top half
    frame[32:, :] = [0, 0, 255]    # Red bottom half

    rich_text = ASCIIFrameConverter.frame_to_half_blocks(frame, target_width=40, target_height=16)
    assert len(rich_text.plain) > 0
    assert "▀" in rich_text.plain


def test_ascii_frame_converter_glyph_mode():
    """Verify luminance-based ASCII character glyph conversion."""
    frame = np.full((32, 32, 3), 200, dtype=np.uint8)  # Bright gray image
    rich_text = ASCIIFrameConverter.frame_to_ascii_chars(frame, target_width=30, target_height=12)
    assert len(rich_text.plain) > 0
    assert not rich_text.plain.isspace()


def test_playback_session_nonexistent_file():
    """Verify graceful handling when video path does not exist."""
    session = VideoPlaybackSession("nonexistent_evidence.mp4")
    assert session.total_frames == 0
    rendered = session.render_current_ascii()
    assert "Video unavailable" in rendered.plain
    session.close()
