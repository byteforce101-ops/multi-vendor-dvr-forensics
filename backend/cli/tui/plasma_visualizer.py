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

PROCESS_PHASES = {
    "idle": {
        "pattern": "Pulse",
        "label": "STANDBY / READY",
        "palette": CYBER_CYAN_PALETTE,
        "speed": 1.0,
        "style": "bold #58a6ff",
    },
    "detect": {
        "pattern": "Matrix",
        "label": "SIGNATURE SCAN",
        "palette": MATRIX_GREEN_PALETTE,
        "speed": 2.2,
        "style": "bold #00ff66",
    },
    "parse": {
        "pattern": "Diamond",
        "label": "GOP SECTOR PARSE",
        "palette": FIRE_AMBER_PALETTE,
        "speed": 1.8,
        "style": "bold #ffaa00",
    },
    "extract": {
        "pattern": "Tunnel",
        "label": "BITSTREAM CARVING",
        "palette": PURPLE_NEON_PALETTE,
        "speed": 2.4,
        "style": "bold #d2a8ff",
    },
    "vision": {
        "pattern": "Warp",
        "label": "TRACEX NEURAL VISION",
        "palette": CYBER_CYAN_PALETTE,
        "speed": 3.0,
        "style": "bold #00ffff",
    },
    "integrity": {
        "pattern": "Interference",
        "label": "CRYPTO SHA-256 AUDIT",
        "palette": CYBER_CYAN_PALETTE,
        "speed": 1.5,
        "style": "bold #79c0ff",
    },
    "reconstruct": {
        "pattern": "Kaleidoscope",
        "label": "SCENARIO RECON",
        "palette": PURPLE_NEON_PALETTE,
        "speed": 1.6,
        "style": "bold #f0883e",
    },
    "query": {
        "pattern": "Spiral",
        "label": "AI AGENT REASONING",
        "palette": FIRE_AMBER_PALETTE,
        "speed": 2.4,
        "style": "bold #ff7b72",
    },
    "complete": {
        "pattern": "Ripple",
        "label": "DOSSIER CERTIFIED",
        "palette": CYBER_CYAN_PALETTE,
        "speed": 1.0,
        "style": "bold #56d364",
    },
}


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
        
        # Process stage synchronization
        self.current_stage = "idle"
        self.stage_label: str | None = None
        self.stage_style: str | None = None
        self.stage_palette: List[Tuple[int, int, int]] | None = None
        self.speed_multiplier: float = 1.0
        
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
        self.stage_label = None
        self.stage_style = None
        self.stage_palette = None
        self.speed_multiplier = 1.0

    def set_pattern_by_name(self, name: str) -> None:
        for i, (p_name, _) in enumerate(PATTERNS):
            if p_name.lower() == name.lower():
                self.pattern_index = i
                break

    def set_process_stage(self, stage: str, custom_label: str | None = None) -> None:
        """Dynamically sync pattern, palette, speed, and status label with executing process."""
        norm_stage = stage.lower().strip()
        self.current_stage = norm_stage
        cfg = PROCESS_PHASES.get(norm_stage, PROCESS_PHASES["idle"])
        self.set_pattern_by_name(cfg["pattern"])
        self.stage_label = custom_label or cfg["label"]
        self.stage_style = cfg["style"]
        self.stage_palette = cfg["palette"]
        self.speed_multiplier = cfg["speed"]

    def render_frame(self, time_step: float = 0.08) -> Text:
        """Calculate and render one mathematical generative frame into a Rich Text widget."""
        self.time += time_step * self.speed_multiplier
        t = self.time
        w = self.width
        h = self.height
        p_name = self.current_pattern_name

        # Select matching thematic palette
        if self.stage_palette is not None:
            palette = self.stage_palette
        elif p_name == "Matrix":
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
        display_label = self.stage_label or f" ◆ {p_name.upper()}"
        if not display_label.startswith(" ◆"):
            display_label = f" ◆ {display_label}"
        display_style = self.stage_style or "bold #58a6ff"
        title_text = Text(display_label, style=display_style)
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
            return (0.15 / d1 + 0.15 / d2 + 0.15 / d3) * 2.0

        elif name == "Moiré":
            # Hypnotic overlapping circle patterns
            d1 = math.hypot(x - 0.4 * math.sin(t * 0.8), y)
            d2 = math.hypot(x + 0.4 * math.sin(t * 0.8), y)
            return math.sin(12.0 * d1) + math.sin(12.0 * d2)

        elif name == "Pulse":
            # Breathing concentric rings from center
            pulse = math.sin(t * 2.0) * 0.3
            return math.sin(8.0 * r - t * 3.0 + pulse) * 3.14

        elif name == "Ripple":
            # Water droplet ripples expanding from center
            return math.sin(10.0 * r - t * 4.0) / (r + 0.4)

        elif name == "Spiral":
            # Tight Archimedean spiral pattern
            return math.sin(theta * 4.0 + r * 8.0 - t * 3.0) * 3.14

        elif name == "Tunnel":
            # Zooming tunnel effect moving in/out from center
            u = theta / math.pi
            v = 1.0 / (r + 0.1) + t * 1.5
            return (math.sin(u * 8.0) * math.cos(v * 4.0)) * 3.14

        elif name == "Vortex":
            # Rotating spiral emanating from the center
            return math.sin(theta * 5.0 - r * 6.0 + t * 4.0) * 3.14

        elif name == "Waves":
            # Horizontal waves with retro scanline feel
            return math.sin(y * 6.0 + math.sin(x * 4.0 + t * 2.0) + t * 1.5) * 3.14

        return math.sin(r * 5.0 - t * 2.0)

    def _render_matrix_frame(self, w: int, h: int, palette: List[Tuple[int, int, int]]) -> Text:
        """Render falling digital matrix rain streaks."""
        grid = [[" " for _ in range(w)] for _ in range(h)]
        styles = [[(0, 0, 0) for _ in range(w)] for _ in range(h)]
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
        display_label = self.stage_label or " ◆ MATRIX RAIN"
        if not display_label.startswith(" ◆"):
            display_label = f" ◆ {display_label}"
        display_style = self.stage_style or "bold #00ff66"
        res.append(Text(display_label, style=display_style))
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
        display_label = self.stage_label or " ◆ WARP DRIVE"
        if not display_label.startswith(" ◆"):
            display_label = f" ◆ {display_label}"
        display_style = self.stage_style or "bold #ffaa00"
        res.append(Text(display_label, style=display_style))
        return res


class LivePlasmaWidget(Static):
    """Textual Widget rendering the live mathematical visualizer at the top right."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.engine = GenerativePatternEngine(width=34, height=11)

    def on_mount(self) -> None:
        """Start 15 FPS animation timer for smooth frame rendering."""
        self.set_interval(0.066, self._tick)

    def _tick(self) -> None:
        """Advance mathematical frame of the current pattern and update widget."""
        self.update(self.engine.render_frame())

    def next_pattern(self) -> None:
        """Switch to next generative pattern when prompted by user."""
        self.engine.next_pattern()
        if self.is_mounted:
            try:
                self.update(self.engine.render_frame())
            except Exception:
                pass

    def set_process_stage(self, stage: str, custom_label: str | None = None) -> None:
        """Update visualizer animation pattern, speed, and status in sync with current process."""
        self.engine.set_process_stage(stage, custom_label)
        if self.is_mounted:
            try:
                self.update(self.engine.render_frame())
            except Exception:
                pass
