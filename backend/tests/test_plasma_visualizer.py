"""Tests for the Generative Mathematical Animation Visualizer (plasma_visualizer.py)."""

import pytest
from backend.cli.tui.plasma_visualizer import (
    PATTERNS,
    GenerativePatternEngine,
    LivePlasmaWidget,
)


def test_all_15_patterns_exist():
    assert len(PATTERNS) == 15
    expected_patterns = [
        "Checkerboard",
        "Classic",
        "Diamond",
        "Interference",
        "Kaleidoscope",
        "Matrix",
        "Metaballs",
        "Moiré",
        "Pulse",
        "Ripple",
        "Spiral",
        "Tunnel",
        "Vortex",
        "Warp",
        "Waves",
    ]
    actual_names = [p[0] for p in PATTERNS]
    for p in expected_patterns:
        assert p in actual_names


def test_pattern_engine_renders_all_patterns():
    engine = GenerativePatternEngine(width=30, height=10)

    for i in range(len(PATTERNS)):
        engine.pattern_index = i
        p_name = engine.current_pattern_name
        assert p_name == PATTERNS[i][0]

        # Render 3 sequential frames
        frame1 = engine.render_frame(0.08)
        frame2 = engine.render_frame(0.08)
        frame3 = engine.render_frame(0.08)

        assert frame1 is not None
        assert frame2 is not None
        assert frame3 is not None
        assert len(frame1.plain) > 0


def test_pattern_cycling_and_lookup():
    engine = GenerativePatternEngine(width=20, height=8)
    initial = engine.current_pattern_name
    assert initial == "Checkerboard"

    engine.next_pattern()
    assert engine.current_pattern_name == "Classic"

    engine.set_pattern_by_name("Matrix")
    assert engine.current_pattern_name == "Matrix"
    frame = engine.render_frame(0.08)
    assert "MATRIX" in frame.plain

    engine.set_pattern_by_name("Warp")
    assert engine.current_pattern_name == "Warp"
    frame = engine.render_frame(0.08)
    assert "WARP" in frame.plain
