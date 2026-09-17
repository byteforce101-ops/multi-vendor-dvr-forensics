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


def test_ascii_frame_converter_full_span_modes():
    """Verify full-span half-blocks, high-contrast, braille, and glyph modes."""
    frame = np.random.randint(40, 180, (480, 640, 3), dtype=np.uint8)

    # Standard half-blocks
    text_hb = ASCIIFrameConverter.frame_to_half_blocks(frame, target_width=80, target_height=20)
    assert "▀" in text_hb.plain

    # Enhanced half-blocks
    text_enh = ASCIIFrameConverter.frame_to_half_blocks(frame, target_width=80, target_height=20, enhance=True)
    assert "▀" in text_enh.plain

    # High-contrast
    text_hc = ASCIIFrameConverter.frame_to_high_contrast(frame, target_width=80, target_height=20)
    assert "▀" in text_hc.plain

    # Braille subpixel matrix
    text_br = ASCIIFrameConverter.frame_to_braille(frame, target_width=40, target_height=10)
    assert len(text_br.plain) > 0


def test_playback_session_controls():
    """Verify playback session mode cycling and enhancement toggling."""
    session = VideoPlaybackSession("nonexistent_evidence.mp4")
    assert session.enhance_enabled is False
    assert session.color_mode == "half_blocks"
    
    # Toggle enhancement
    session.toggle_enhancement()
    assert session.enhance_enabled is True

    # Cycle modes
    initial_mode = session.color_mode
    new_mode = session.cycle_mode()
    assert new_mode != initial_mode
    status = session.get_status_line()
    assert "Mode:" in status
    session.close()


