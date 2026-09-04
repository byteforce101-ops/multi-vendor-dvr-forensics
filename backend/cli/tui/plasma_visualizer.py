"""backend/cli/tui/plasma_visualizer.py — Generative Mathematical Visualizer.

Implements 15 live generative mathematical animation patterns:
1. Checkerboard   — Pulsating checkerboard with wave distortion
2. Classic        — Traditional sine wave plasma with layered oscillations
3. Diamond        — Diamond-shaped patterns using Manhattan distance
4. Interference   — Multiple circular waves creating interference patterns
5. Kaleidoscope   — Symmetrical kaleidoscope reflections
6. Matrix         — Falling vertical streaks like digital rain
7. Metaballs      — Organic blobs that merge and separate
8. Moiré          — Hypnotic overlapping circle patterns
9. Pulse          — Breathing concentric rings from center
10. Ripple        — Water droplet ripples expanding from center
11. Spiral        — Tight Archimedean spiral pattern
12. Tunnel        — Zooming tunnel effect moving in/out from center
13. Vortex        — Rotating spiral emanating from the center
14. Warp          — Starfield warp drive speed effect
15. Waves         — Horizontal waves with retro scanline feel
"""

from __future__ import annotations

import math
import random
from typing import List, Tuple
from rich.text import Text
from textual.widgets import Static

PATTERNS = [
    ("Checkerboard", "Pulsating checkerboard with wave distortion"),
    ("Classic", "Traditional sine wave plasma with layered oscillations"),
    ("Diamond", "Diamond-shaped patterns using Manhattan distance"),
    ("Interference", "Multiple circular waves creating interference patterns"),
    ("Kaleidoscope", "Symmetrical kaleidoscope reflections"),
    ("Matrix", "Falling vertical streaks like digital rain"),
    ("Metaballs", "Organic blobs that merge and separate"),
    ("Moiré", "Hypnotic overlapping circle patterns"),
    ("Pulse", "Breathing concentric rings from center"),
    ("Ripple", "Water droplet ripples expanding from center"),
    ("Spiral", "Tight Archimedean spiral pattern"),
    ("Tunnel", "Zooming tunnel effect moving in/out from center"),
    ("Vortex", "Rotating spiral emanating from the center"),
    ("Warp", "Starfield warp drive speed effect"),
    ("Waves", "Horizontal waves with retro scanline feel"),
]

# Forensic Cyber Color Palettes
CYBER_CYAN_PALETTE = [
    (10, 25, 47),    # deep navy
    (0, 78, 137),    # steel blue
    (0, 150, 214),   # electric blue
    (0, 220, 237),   # vivid cyan
    (88, 240, 255),  # neon cyan
    (220, 255, 255), # ice white
]

MATRIX_GREEN_PALETTE = [
    (0, 20, 5),
    (0, 60, 15),
    (0, 140, 35),
    (0, 220, 65),
    (120, 255, 140),
    (240, 255, 240),
]

PURPLE_NEON_PALETTE = [
    (25, 5, 40),
    (70, 10, 100),
    (140, 30, 180),
    (200, 60, 240),
    (240, 140, 255),
    (255, 230, 255),
]

FIRE_AMBER_PALETTE = [
    (30, 10, 0),
    (90, 25, 0),
    (180, 70, 0),
    (240, 140, 0),
    (255, 210, 50),
    (255, 255, 230),
]

DENSITY_CHARS = " .:-=+*#%@"


def _sample_palette(val: float, palette: List[Tuple[int, int, int]]) -> Tuple[int, int, int]:
    """Sample an interpolated RGB color from a palette for normalized val in [0.0, 1.0]."""
    val = max(0.0, min(1.0, val))
    n = len(palette) - 1
    idx_f = val * n
    idx0 = int(idx_f)
    idx1 = min(idx0 + 1, n)
    frac = idx_f - idx0
    c0 = palette[idx0]
    c1 = palette[idx1]
    r = int(c0[0] + (c1[0] - c0[0]) * frac)
    g = int(c0[1] + (c1[1] - c0[1]) * frac)
    b = int(c0[2] + (c1[2] - c0[2]) * frac)
    return (r, g, b)


class GenerativePatternEngine:
    """Mathematical generator for all 15 generative visualizer patterns."""

    def __init__(self, width: int = 34, height: int = 11):
        self.width = width
        self.height = height
        self.pattern_index = 0
        self.time = 0.0
        self.palette = CYBER_CYAN_PALETTE
        
        # Matrix rain state
        self._matrix_drops = [random.uniform(0, 20) for _ in range(self.width)]
        self._matrix_speeds = [random.uniform(0.4, 1.2) for _ in range(self.width)]
        
        # Warp stars state
        self._warp_stars = [
            (random.uniform(-1.0, 1.0), random.uniform(-1.0, 1.0), random.uniform(0.1, 1.0))
            for _ in range(40)
        ]

    @property
    def current_pattern_name(self) -> str:
        return PATTERNS[self.pattern_index % len(PATTERNS)][0]

    @property
    def current_pattern_desc(self) -> str:
        return PATTERNS[self.pattern_index % len(PATTERNS)][1]

    def next_pattern(self) -> None:
        self.pattern_index = (self.pattern_index + 1) % len(PATTERNS)

    def set_pattern_by_name(self, name: str) -> None:
        for i, (p_name, _) in enumerate(PATTERNS):
            if p_name.lower() == name.lower():
                self.pattern_index = i
                break

    def render_frame(self, time_step: float = 0.08) -> Text:
        """Calculate and render one mathematical generative frame into a Rich Text widget."""
        self.time += time_step
        t = self.time
        w = self.width
        h = self.height
        p_name = self.current_pattern_name

        # Select matching thematic palette
        if p_name == "Matrix":
            palette = MATRIX_GREEN_PALETTE
        elif p_name in ("Kaleidoscope", "Vortex", "Tunnel"):
            palette = PURPLE_NEON_PALETTE
        elif p_name in ("Diamond", "Warp"):
            palette = FIRE_AMBER_PALETTE
        else:
            palette = CYBER_CYAN_PALETTE

        # -------------------------------------------------------------
        # 1. SPECIAL CASE: MATRIX DIGITAL RAIN
        # -------------------------------------------------------------
        if p_name == "Matrix":
            return self._render_matrix_frame(w, h, palette)

        # -------------------------------------------------------------
        # 2. SPECIAL CASE: WARP STARFIELD
        # -------------------------------------------------------------
        if p_name == "Warp":
            return self._render_warp_frame(w, h, palette)

        # -------------------------------------------------------------
        # 3. MATHEMATICAL FIELD GENERATORS (Checkerboard, Classic, etc.)
        # -------------------------------------------------------------
        lines: List[Text] = []
        aspect_ratio = 2.0  # Terminal characters are ~2x taller than wide

        for y_idx in range(h):
            line = Text()
            y = (y_idx / max(1, h - 1)) * 2.0 - 1.0
            
            for x_idx in range(w):
                x = ((x_idx / max(1, w - 1)) * 2.0 - 1.0) * aspect_ratio
                val = self._evaluate_pattern(p_name, x, y, t)
                
                # Normalize val to [0, 1]
                norm_val = 0.5 + 0.5 * math.sin(val)
                r, g, b = _sample_palette(norm_val, palette)
                
                # Pick character density glyph
                char_idx = int(norm_val * (len(DENSITY_CHARS) - 1))
                char = DENSITY_CHARS[char_idx]
                
                line.append(char, style=f"#{r:02x}{g:02x}{b:02x}")
            lines.append(line)

        # Append title footer line
        title_text = Text(f" ◆ {p_name.upper()}", style="bold #58a6ff")
        res = Text("\n").join(lines)
        res.append("\n")
        res.append(title_text)
        return res

    def _evaluate_pattern(self, name: str, x: float, y: float, t: float) -> float:
        """Evaluate mathematical function at coordinate (x, y) and time t."""
        r = math.sqrt(x * x + y * y) + 1e-6
        theta = math.atan2(y, x)

        if name == "Checkerboard":
            # Pulsating checkerboard with wave distortion
            u = x + 0.35 * math.sin(3.0 * y + t)
            v = y + 0.35 * math.cos(3.0 * x + t)
            return math.sin(6.0 * u) * math.sin(6.0 * v) * 3.14

        elif name == "Classic":
            # Traditional sine wave plasma with layered oscillations
            v1 = math.sin(x * 3.5 + t)
            v2 = math.sin(y * 3.5 - t * 1.2)
            v3 = math.sin((x + y) * 2.5 + t * 0.8)
            v4 = math.sin(r * 4.0 - t * 2.0)
            return (v1 + v2 + v3 + v4) * 1.5

        elif name == "Diamond":
            # Diamond-shaped patterns using Manhattan distance
            cos_t, sin_t = math.cos(t * 0.5), math.sin(t * 0.5)
            rx = x * cos_t - y * sin_t
            ry = x * sin_t + y * cos_t
            d = abs(rx) + abs(ry)
            return math.sin(7.0 * d - 3.0 * t) * 3.14

        elif name == "Interference":
            # Multiple circular waves creating interference patterns
            c1_x, c1_y = 0.5 * math.cos(t), 0.5 * math.sin(t)
            c2_x, c2_y = -0.5 * math.cos(t * 0.8), -0.5 * math.sin(t * 0.8)
            d1 = math.hypot(x - c1_x, y - c1_y)
            d2 = math.hypot(x - c2_x, y - c2_y)
            return (math.sin(9.0 * d1 - 4.0 * t) + math.sin(9.0 * d2 - 4.0 * t)) * 2.0

        elif name == "Kaleidoscope":
            # Symmetrical kaleidoscope reflections (6-fold)
            angle = (theta + t * 0.4) % (math.pi / 3.0)
            sym_angle = abs(angle - (math.pi / 6.0))
            kx = r * math.cos(sym_angle)
            ky = r * math.sin(sym_angle)
            return (math.sin(5.0 * kx) * math.cos(5.0 * ky + t)) * 3.14

        elif name == "Metaballs":
            # Organic blobs that merge and separate
            b1_x, b1_y = 0.5 * math.sin(t * 1.1), 0.5 * math.cos(t * 0.9)
            b2_x, b2_y = 0.5 * math.cos(t * 0.7), 0.5 * math.sin(t * 1.3)
            b3_x, b3_y = 0.3 * math.sin(t * 1.5), 0.3 * math.cos(t * 1.7)
            d1 = (x - b1_x) ** 2 + (y - b1_y) ** 2 + 0.08
            d2 = (x - b2_x) ** 2 + (y - b2_y) ** 2 + 0.08
            d3 = (x - b3_x) ** 2 + (y - b3_y) ** 2 + 0.08
            field = 0.15 / d1 + 0.15 / d2 + 0.12 / d3
            return field * 4.0 - t * 2.0

        elif name == "Moiré":
            # Hypnotic overlapping circle patterns
            shift = 0.25 * math.sin(t * 1.2)
            d1 = math.hypot(x - shift, y)
            d2 = math.hypot(x + shift, y)
            return math.sin(12.0 * d1) * math.sin(12.0 * d2) * 3.14

        elif name == "Pulse":
            # Breathing concentric rings from center
            breath = 1.0 + 0.35 * math.sin(t * 2.5)
            return math.sin(8.0 * r * breath - t * 4.0) * 3.14

        elif name == "Ripple":
            # Water droplet ripples expanding from center
            decay = 1.0 / (1.0 + 1.8 * r)
            return math.cos(10.0 * r - t * 5.0) * decay * 4.0

        elif name == "Spiral":
            # Tight Archimedean spiral pattern
            return math.sin(8.0 * r - 4.0 * theta + t * 3.0) * 3.14

        elif name == "Tunnel":
            # Zooming tunnel effect moving in/out from center
            u = 3.0 / r + t * 2.5
            v = theta * 3.0 / math.pi
            return (math.sin(u) * math.cos(v * 3.14)) * 3.14

        elif name == "Vortex":
            # Rotating spiral emanating from the center
            rot_r = r * 6.0
            return math.sin(rot_r - 3.0 * theta - t * 4.0) * 3.14

        elif name == "Waves":
            # Horizontal waves with retro scanline feel
            w1 = math.sin(6.0 * y + 2.0 * math.sin(3.0 * x + t) + t * 2.0)
            w2 = math.cos(3.0 * x - t)
            return (w1 + w2) * 2.5

        return math.sin(r * 5.0 - t * 2.0)

    def _render_matrix_frame(self, w: int, h: int, palette: List[Tuple[int, int, int]]) -> Text:
        """Render animated falling green digital matrix rain."""
        grid = [[" " for _ in range(w)] for _ in range(h)]
        styles = [[(0, 20, 5) for _ in range(w)] for _ in range(h)]
        chars = "0123456789ABCDEF$#@*+=-:"

        for col in range(w):
            self._matrix_drops[col] += self._matrix_speeds[col] * 0.4
            if self._matrix_drops[col] > h + 10:
                self._matrix_drops[col] = random.uniform(-6, 0)
                self._matrix_speeds[col] = random.uniform(0.4, 1.2)

            head = int(self._matrix_drops[col])
            tail_len = 6

            for i in range(tail_len):
                row = head - i
                if 0 <= row < h:
                    grid[row][col] = random.choice(chars)
                    if i == 0:
                        styles[row][col] = palette[-1]  # Bright lead drop
                    else:
                        frac = max(0.0, 1.0 - (i / tail_len))
                        styles[row][col] = _sample_palette(frac * 0.8, palette)

        lines: List[Text] = []
        for r_idx in range(h):
            line = Text()
            for c_idx in range(w):
                ch = grid[r_idx][c_idx]
                r, g, b = styles[r_idx][c_idx]
                line.append(ch, style=f"#{r:02x}{g:02x}{b:02x}")
            lines.append(line)

        res = Text("\n").join(lines)
        res.append("\n")
        res.append(Text(" ◆ MATRIX RAIN", style="bold #00ff66"))
        return res

    def _render_warp_frame(self, w: int, h: int, palette: List[Tuple[int, int, int]]) -> Text:
        """Render 3D starfield warp drive speed effect."""
        grid = [[" " for _ in range(w)] for _ in range(h)]
        styles = [[(0, 0, 0) for _ in range(w)] for _ in range(h)]

        cx, cy = w / 2.0, h / 2.0
        new_stars = []

        for sx, sy, sz in self._warp_stars:
            sz -= 0.05  # Move star closer
            if sz <= 0.05:
                sx = random.uniform(-1.0, 1.0)
                sy = random.uniform(-1.0, 1.0)
                sz = 1.0

            px = int(cx + (sx / sz) * (w * 0.45))
            py = int(cy + (sy / sz) * (h * 0.45))

            if 0 <= px < w and 0 <= py < h:
                bright = min(1.0, (1.0 - sz) * 1.3)
                ch = "*" if sz < 0.3 else ("+" if sz < 0.6 else ".")
                grid[py][px] = ch
                styles[py][px] = _sample_palette(bright, palette)

            new_stars.append((sx, sy, sz))

        self._warp_stars = new_stars

        lines: List[Text] = []
        for r_idx in range(h):
            line = Text()
            for c_idx in range(w):
                ch = grid[r_idx][c_idx]
                r, g, b = styles[r_idx][c_idx]
                line.append(ch, style=f"#{r:02x}{g:02x}{b:02x}")
            lines.append(line)

        res = Text("\n").join(lines)
        res.append("\n")
        res.append(Text(" ◆ WARP DRIVE", style="bold #ffaa00"))
        return res


class LivePlasmaWidget(Static):
    """Textual Widget rendering the live mathematical visualizer at the top right."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.engine = GenerativePatternEngine(width=34, height=11)
        self._pattern_cycle_counter = 0

    def on_mount(self) -> None:
        """Start 15 FPS animation timer and 8-second pattern cycling."""
        self.set_interval(0.066, self._tick)

    def _tick(self) -> None:
        """Advance mathematical frame and update widget."""
        self._pattern_cycle_counter += 1
        # Auto-switch pattern every 120 ticks (~8 seconds)
        if self._pattern_cycle_counter >= 120:
            self._pattern_cycle_counter = 0
            self.engine.next_pattern()
        self.update(self.engine.render_frame())

    def next_pattern(self) -> None:
        self.engine.next_pattern()
        self._pattern_cycle_counter = 0
        self.update(self.engine.render_frame())
