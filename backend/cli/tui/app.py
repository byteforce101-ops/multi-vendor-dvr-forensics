"""backend/cli/tui/app.py — TraceX full-screen Terminal User Interface.

Clean, uncluttered, highly readable 50/50 split forensic workspace:
┌──────────────────────────────────────────────────────────────────────────┐
│ TraceX Original ASCII Logo                                               │
│                                                                          │
│ ┌────────────────────────────────┐  ┌─────────────────────────────────┐ │
│ │  QUERY RESULTS                 │  │  AI FORENSIC ANALYSIS           │ │
│ │  (Clean Q&A Investigation Log) │  │  (Complete untruncated records, │ │
│ │  50% width                     │  │   events, integrity, summary)   │ │
│ └────────────────────────────────┘  └─────────────────────────────────┘ │
│                                                                          │
│ ┌──────────────────────────────────────────────────────────────────────┐ │
│ │  query / evidence path input bar (OS clipboard paste-ready)          │ │
│ └──────────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────┘
"""

from __future__ import annotations

import math
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from rich.text import Text
from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.widgets import Input, Static

from backend.cli.tui.engine import (
    PipelineResult,
    QueryAnswer,
    TraceXPipelineEngine,
    human_size,
    safe_event_sort_key,
)

from backend.cli.tui.plasma_visualizer import LivePlasmaWidget

# Original TraceX ASCII logo from attached specification
ORIGINAL_ASCII_LOGO = r"""        .                                                                   
      -===-=-                .                                              
    :=::=+**++-:             +                                              
    =+==----=*==-.           +                                              
    :---.=--=:=:===.         +    *@@@@@@@@=:@@@@@@@@=    #@@@=    *@@@@@@%. #@@@@@@@+.%@%. #@@:
    ===+=::===:-*++          +       =@@-   :@@+   #@@.  *@%-@@-  #@@.   *#+ #@@.       *@@@@#  
    .==+*+:=:-=+.+=-.        +       =@@-   :@@@@@@@#   -@@=:%@@. %@@        #@@%%%%:   :@@@@-  
     .-=:=+--+-==+++-.       +       =@@-   :@@+  =@@* -@@@@@@@@%.=@@#=-#@@+ #@@*++++- +@@+=@@# 
      --+=-=+*-=.---=-       +       -%%-   :%%=   -%%=%%*    .%%*  -%@@%+   *%%%%%%%+%%%:  .%%%.
       .+-++*=-:=:-::        +                                              
         .====--:..          +                                              
           . :.:."""

COMPACT_LOGO = r"""  ██████ ██████   █████   ██████ ███████ ██   ██
    ██   ██   ██ ██   ██ ██      ██       ██ ██ 
    ██   ██████  ███████ ██      █████     ███  
    ██   ██   ██ ██   ██ ██      ██       ██ ██ 
    ██   ██   ██ ██   ██  ██████ ███████ ██   ██"""


def _rule(length: int = 50) -> str:
    """Return a clean subtle divider line."""
    return f"[dim]{'─' * length}[/dim]"


def _section_header(title: str, count: str = "") -> str:
    """Render a clean, high-contrast section title without artificial boxes."""
    c_str = f" [dim]({count})[/dim]" if count else ""
    return f"[bold bright_cyan]▶ {title}[/bold bright_cyan]{c_str}\n{_rule(56)}"


TUI_CSS = """
Screen {
    background: #000000;
    color: #e6edf3;
}

#header-box {
    dock: top;
    height: 13;
    layout: horizontal;
    align: left middle;
    padding: 0 1;
    margin-bottom: 0;
}

#logo-widget {
    width: 1fr;
    height: 100%;
    color: #58a6ff;
    content-align: left middle;
}

#plasma-widget {
    width: 38;
    height: 100%;
    border: round #30363d;
    background: #05070a;
    padding: 0 1;
    content-align: center middle;
}

#plasma-widget:focus-within {
    border: round #58a6ff;
}

#tab-bar {
    height: 1;
    color: #8b949e;
    background: #0d1117;
    padding: 0 2;
    margin: 0 1;
    border-bottom: solid #30363d;
}

#main-panels-container {
    height: 1fr;
    width: 100%;
    layout: horizontal;
    margin: 0;
    padding: 0 1;
}

#query-results-panel {
    width: 50%;
    height: 100%;
    border: round #30363d;
    background: #080a0f;
    padding: 1 2;
    margin-right: 1;
}

#query-results-panel:focus-within {
    border: round #58a6ff;
}

#additional-analysis-panel {
    width: 50%;
    height: 100%;
    border: round #30363d;
    background: #080a0f;
    padding: 1 2;
}

#additional-analysis-panel:focus-within {
    border: round #58a6ff;
}

#video-player-panel {
    width: 100%;
    height: 100%;
    border: round #30363d;
    background: #080a0f;
    padding: 1 2;
    display: none;
}

#video-player-panel:focus-within {
    border: round #58a6ff;
}

#ascii-video-screen {
    height: 1fr;
    width: 100%;
    background: #000000;
    border: solid #21262d;
    padding: 0;
    content-align: center middle;
}

#ascii-video-status {
    height: auto;
    color: #58a6ff;
    padding: 0 1;
    margin-top: 1;
}

#search-bar-wrapper {
    dock: bottom;
    height: auto;
    padding: 0 1 1 1;
}

#search-box {
    border: round #30363d;
    background: #0d1117;
    height: 3;
    padding: 0 1;
}

#search-box:focus-within {
    border: round #58a6ff;
}

#search-input {
    border: none;
    background: transparent;
    color: #ffffff;
    height: 1;
    padding: 0;
}

#search-input:focus {
    border: none;
}

#footer-bar {
    height: 1;
    color: #8b949e;
    align: center middle;
    margin-top: 0;
}
"""


class TraceXHeader(Static):
    """Header widget displaying the animated TraceX ASCII art logo in shimmering shades of blue."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.time: float = 0.0

    def on_mount(self) -> None:
        self.set_interval(0.066, self._tick)

    def _tick(self) -> None:
        self.time += 0.08
        self.update(self._generate_colored_logo())

    def _generate_colored_logo(self) -> Text:
        width = self.size.width or 100
        t = self.time

        if width >= 75:
            res = Text()
            lines = ORIGINAL_ASCII_LOGO.splitlines()
            for y_idx, line in enumerate(lines):
                if not line:
                    res.append("\n")
                    continue

                idx_div = line.find("+")
                for x_idx, ch in enumerate(line):
                    if ch == " ":
                        res.append(" ")
                        continue

                    if idx_div != -1 and x_idx == idx_div:
                        # Animated pulsing divider
                        div_wave = 0.5 + 0.5 * math.sin(t * 2.0 + y_idx * 0.25)
                        r = int(20 + 30 * div_wave)
                        g = int(100 + 80 * div_wave)
                        b = int(220 + 35 * div_wave)
                        res.append(ch, style=f"bold #{r:02x}{g:02x}{b:02x}")
                    elif idx_div != -1 and x_idx > idx_div:
                        # TRACEX typography: Dynamic shimmering wave from sapphire to electric cyan
                        phase = t * 2.2 + x_idx * 0.08 + y_idx * 0.15
                        wave = 0.5 + 0.5 * math.sin(phase)
                        wave2 = 0.5 + 0.5 * math.cos(t * 1.5 - x_idx * 0.05 + y_idx * 0.1)
                        r = int(10 + 50 * wave2)
                        g = int(140 + 95 * wave)
                        b = int(215 + 40 * wave2)
                        res.append(ch, style=f"bold #{r:02x}{g:02x}{b:02x}")
                    else:
                        # Radar reticle on left: Concentric radar shades of blue
                        phase = t * 1.8 + x_idx * 0.12 - y_idx * 0.18
                        wave = 0.5 + 0.5 * math.sin(phase)
                        r = int(5 + 35 * wave)
                        g = int(75 + 90 * wave)
                        b = int(170 + 85 * wave)
                        res.append(ch, style=f"#{r:02x}{g:02x}{b:02x}")
                res.append("\n")
            return res
        else:
            t_wave = 0.5 + 0.5 * math.sin(t * 2.0)
            g_val = int(140 + 90 * t_wave)
            comp = Text(COMPACT_LOGO, style=f"bold #10{g_val:02x}ff")
            comp.append("\n  TRACE  ·  RECOVER  ·  ANALYZE", style="bold #58a6ff")
            return comp

    def render(self) -> Text:
        return self._generate_colored_logo()


def clean_pasted_path(text: str) -> str:
    """Sanitize a pasted file path or query string.

    Removes terminal bracketed paste residues (0~, 200~, 201~, \x1b[200~),
    PowerShell call syntax (& '...', & "..."), surrounding quotes,
    and accidental duplicate concatenations (e.g. pathpath).
    """
    if not text:
        return ""
    clean = text.strip()

    # 1. Strip bracketed paste escape sequences and ConPTY residues (0~, 200~, 201~, \x1b[200~, ^[[200~)
    clean = re.sub(r"^(0~|200~|201~|\x1b\[\d+~|\^\[\[\d+~)+", "", clean).strip()
    clean = re.sub(r"(0~|200~|201~|\x1b\[\d+~|\^\[\[\d+~)+$", "", clean).strip()

    # 2. Strip PowerShell command invocation prefix (& '...' or & "...")
    if clean.startswith("&"):
        clean = clean[1:].strip()

    # 3. Strip surrounding quotes
    if (clean.startswith('"') and clean.endswith('"')) or (clean.startswith("'") and clean.endswith("'")):
        clean = clean[1:-1].strip()

    # 4. Check for exact duplicate string doubling (e.g. 'pathpath' or 'path path')
    if len(clean) > 4 and len(clean) % 2 == 0:
        half = len(clean) // 2
        if clean[:half] == clean[half:]:
            clean = clean[:half]

    parts = clean.split(" ")
    if len(parts) == 2 and parts[0] == parts[1]:
        clean = parts[0]

    # Doubled with extension boundary: e.g. 'foo.mp4foo.mp4'
    m_ext = re.match(r"^(.*?(\.mp4|\.dd|\.avi|\.mkv|\.mov|\.bin|\.img|\.ts))\s*\1$", clean, re.IGNORECASE)
    if m_ext:
        clean = m_ext.group(1)

    # 5. If multiple drive paths exist (e.g. C:\foo.mp4C:\foo.mp4 or C:\foo.mp40~C:\foo.mp4), split on drive boundaries
    drive_indices = [m.start() for m in re.finditer(r"[A-Za-z]:[/\\]", clean)]
    if len(drive_indices) >= 2:
        cand = clean[drive_indices[0]:drive_indices[1]]
        cand = re.sub(r"(\x1b\[\d+~|\^\[\[\d+~|0~|200~|201~)+$", "", cand)
        clean = cand.rstrip("\"' \t\r\n")
    elif drive_indices:
        clean = clean[drive_indices[0]:].rstrip("\"' ")

    # 6. Collapse internal newlines/carriage returns
    clean = clean.replace("\r\n", " ").replace("\n", " ").strip()
    return clean


class PasteableInput(Input):
    """Input widget that cleanly supports OS clipboard paste with debouncing and duplicate suppression."""

    BINDINGS = [
        *Input.BINDINGS,
        Binding("shift+insert", "paste", "Paste", show=False),
    ]

    _last_paste_time: float = 0.0
    _last_paste_val: str = ""

    def action_paste(self) -> None:
        """Single authoritative paste action that reads directly from the OS clipboard."""
        from backend.cli.tui.clipboard import get_clipboard_text

        text = get_clipboard_text() or self.app.clipboard
        if text:
            self._insert_sanitized(text)

    def _on_paste(self, event) -> None:
        """Override Textual's default paste handler to sanitize artifacts and prevent duplicate paste."""
        event.stop()
        if hasattr(event, "text") and event.text:
            self._insert_sanitized(event.text)

    def _insert_sanitized(self, raw_text: str) -> None:
        """Sanitize text, debounce fast duplicate paste events, and replace or insert cleanly."""
        import time

        now = time.time()
        clean = clean_pasted_path(raw_text)
        if not clean:
            return

        # Debounce duplicate terminal paste: if input already contains the text or rapid duplicate paste
        if self.value and (now - self._last_paste_time < 0.4) and (clean == self._last_paste_val or clean in self.value):
            return

        self._last_paste_time = now
        self._last_paste_val = clean

        # In file ingestion mode or if the box only contains whitespace, replace the entire input value
        if getattr(self.app, "mode", "file") == "file" or not self.value.strip():
            self.value = clean
            self.cursor_position = len(clean)
        else:
            # Prevent appending identical text if it was already inserted
            if self.value.endswith(clean):
                return
            start, end = self.selection
            self.replace(clean, start, end)

    def watch_value(self, old_value: str, new_value: str) -> None:
        """Automatically detect and fix duplicate paths if typed or pasted by the terminal stream."""
        if getattr(self.app, "mode", "file") == "file" and new_value:
            deduped = clean_pasted_path(new_value)
            if deduped != new_value and len(deduped) < len(new_value):
                self.value = deduped
                self.cursor_position = len(deduped)


from backend.video.playback.ascii_player import VideoPlaybackSession


class TraceXApp(App):
    """TraceX Full-Screen Forensic Terminal User Interface."""

    CSS = TUI_CSS
    TITLE = "TraceX Forensic Intelligence Platform"
    BINDINGS = [
        Binding("enter", "submit_input", "Submit", show=False),
        Binding("ctrl+o", "new_file", "Upload File", show=True),
        Binding("ctrl+n", "new_file", "Upload File", show=False),
        Binding("f1", "show_tab_query", "Query Tab", show=True),
        Binding("1", "show_tab_query", "Query Tab", show=False),
        Binding("f2", "show_tab_analysis", "AI Dossier Tab", show=True),
        Binding("2", "show_tab_analysis", "AI Dossier Tab", show=False),
        Binding("f3", "show_tab_video", "Carved Video (ASCII)", show=True),
        Binding("3", "show_tab_video", "Carved Video (ASCII)", show=False),
        Binding("f4", "show_tab_split", "Split View", show=True),
        Binding("0", "show_tab_split", "Split View", show=False),
        Binding("ctrl+m", "toggle_maximize", "Maximize/Restore", show=False),
        Binding("tab", "switch_focus", "Next Panel", show=True),
        Binding("shift+tab", "switch_focus_reverse", "Prev Panel", show=False),
        Binding("space", "toggle_video_play", "Play/Pause Video", show=False),
        Binding("left", "video_seek_prev", "Seek Prev Frame", show=False),
        Binding("right", "video_seek_next", "Seek Next Frame", show=False),
        Binding("bracket_left", "video_seek_prev_second", "Rewind 1s", show=False),
        Binding("bracket_right", "video_seek_next_second", "Forward 1s", show=False),
        Binding("r", "video_restart", "Restart Video", show=False),
        Binding("m", "video_toggle_mode", "Toggle Color Mode", show=False),
        Binding("p", "next_plasma_pattern", "Cycle Animation Pattern", show=False),
        Binding("escape", "clear_or_focus_search", "Clear / Focus", show=True),
        Binding("ctrl+c", "quit", "Exit", show=True),
        Binding("ctrl+q", "quit", "Exit", show=False),
    ]

    def __init__(self, default_file_path: str | None = None, initial_query: str | None = None):
        super().__init__()
        self.engine = TraceXPipelineEngine()
        self.default_file_path = default_file_path
        self.initial_query = initial_query
        self.mode = "file"  # "file" -> waiting for file; "query" -> asking questions
        self.view_mode = "split"  # "split" | "query" | "analysis" | "video"
        self.playback_session: Optional[VideoPlaybackSession] = None
        self._playback_timer = None

    @property
    def clipboard(self) -> str:
        """Read directly from the OS system clipboard."""
        from backend.cli.tui.clipboard import get_clipboard_text

        text = get_clipboard_text()
        if text:
            return text
        return self._clipboard

    @clipboard.setter
    def clipboard(self, value: str) -> None:
        self._clipboard = value
        from backend.cli.tui.clipboard import set_clipboard_text

        set_clipboard_text(value)

    def compose(self) -> ComposeResult:
        # 1. Header with Attached ASCII Logo (Left) and Live Generative Plasma Animation (Right)
        with Horizontal(id="header-box"):
            yield TraceXHeader(id="logo-widget")
            yield LivePlasmaWidget(id="plasma-widget")

        # 2. Interactive Tab Navigation Bar
        yield Static(self._get_tab_bar_text(), id="tab-bar")

        # 3. Main Content Split / Tab Container
        with Horizontal(id="main-panels-container"):
            with VerticalScroll(id="query-results-panel"):
                yield Static(
                    self._get_file_prompt_text(),
                    id="query-results-content",
                )
            with VerticalScroll(id="additional-analysis-panel"):
                yield Static(
                    self._get_initial_analysis_placeholder_text(),
                    id="additional-analysis-content",
                )
            with Vertical(id="video-player-panel"):
                yield Static(
                    Text("No video stream loaded. Ingest an evidence file to activate ASCII player.", style="dim yellow center"),
                    id="ascii-video-screen",
                )
                yield Static(
                    "[bold dim]Controls: [SPACE] Play/Pause  [ [ / ] ] Seek 1s  [← / →] Step  [R] Restart  [M] Mode  [1-3,0] Switch Tabs[/bold dim]",
                    id="ascii-video-status",
                )

        # 4. Bottom Search / File Input Bar (Pasteable from OS Clipboard)
        with Vertical(id="search-bar-wrapper"):
            with Container(id="search-box"):
                yield PasteableInput(
                    placeholder="Enter evidence / video file path...",
                    id="search-input",
                )
            yield Static(
                "[bold #58a6ff]ENTER[/] Submit   [bold #58a6ff]1[/] Query Log   [bold #58a6ff]2[/] AI Dossier   [bold #58a6ff]3[/] ASCII Video   [bold #58a6ff]0[/] Split View   [bold #58a6ff]P[/] Pattern   [bold #58a6ff]CTRL+O[/] Upload   [bold #58a6ff]ESC[/] Return",
                id="footer-bar",
            )

    def on_mount(self) -> None:
        """Set border titles, focus the input bar, and initialize playback timer."""
        q_panel = self.query_one("#query-results-panel", VerticalScroll)
        a_panel = self.query_one("#additional-analysis-panel", VerticalScroll)
        v_panel = self.query_one("#video-player-panel", Vertical)
        q_panel.border_title = "QUERY RESULTS"
        a_panel.border_title = "AI FORENSIC ANALYSIS"
        v_panel.border_title = "CARVED VIDEO (ASCII PLAYER)"
        self.query_one("#search-input", PasteableInput).focus()

        # Start background 15 FPS playback ticker
        self._playback_timer = self.set_interval(0.066, self._on_playback_tick)

        if self.default_file_path:
            inp = self.query_one("#search-input", PasteableInput)
            inp.value = self.default_file_path
            self.action_submit_input()

    def _get_tab_bar_text(self) -> str:
        """Generate high-contrast tab selector line with active tab indicator."""
        tabs = [
            ("1", "Query & Q&A", "query"),
            ("2", "AI Forensic Dossier", "analysis"),
            ("3", "Carved Video (ASCII)", "video"),
            ("0", "Split Multi-Panel", "split"),
        ]
        parts = []
        for key, label, mode in tabs:
            if self.view_mode == mode:
                parts.append(f"[bold black on #58a6ff] [{key}] {label} [/bold black on #58a6ff]")
            else:
                parts.append(f"[bold #58a6ff][{key}][/bold #58a6ff] {label}")
        return "   ".join(parts)

    def _get_file_prompt_text(self) -> str:
        lines = [
            "[bold white]Step 1 / 2 — Evidence File Ingestion[/bold white]",
            _rule(48),
            "",
            "Please provide a digital video file or raw DVR disk image.",
            "Type or paste the file path in the search bar below and press [bold bright_cyan]\\[ENTER][/bold bright_cyan].",
            "",
            "[bold white]Supported Formats:[/bold white]",
            "  • [bold cyan]Video Containers:[/bold cyan]  .mp4, .avi, .mkv, .mov, .ts, .asf",
            "  • [bold cyan]DVR Stream Dumps:[/bold cyan]  Hikvision, Dahua, HeimVision, CP-Plus, Xiongmai",
            "  • [bold cyan]Raw Disk Images:[/bold cyan]   .dd, .img, .bin, .raw, .001",
            "",
            "[dim]Tip: You can use Ctrl+V to paste file paths directly from Windows Explorer.[/dim]",
        ]
        return "\n".join(lines)

    def _get_initial_analysis_placeholder_text(self) -> str:
        lines = [
            "[dim]Awaiting evidence ingestion...[/dim]",
            _rule(48),
            "",
            "When an evidence file is ingested, TraceX executes the full forensic pipeline:",
            "",
            "  1. [cyan]Signature & DVR Vendor Detection[/cyan]",
            "  2. [cyan]Stream Parsing & Recording Discovery[/cyan]",
            "  3. [cyan]Playable Video Carving & Stream Extraction[/cyan]",
            "  4. [cyan]AI Vision & Adaptive Motion Analysis[/cyan]",
            "  5. [cyan]Forensic Event Reconstruction & Scenario Clustering[/cyan]",
            "  6. [cyan]Final Incident Forensic Summary[/cyan]",
            "  7. [cyan]Video Stream Integrity & Tampering Analysis[/cyan]",
            "  8. [cyan]Object Disappearance & Continuity Detection[/cyan]",
            "",
            "[dim]All forensic telemetry will populate here automatically.[/dim]",
        ]
        return "\n".join(lines)

    def action_show_tab_query(self) -> None:
        """Switch to Query Results & Q&A tab (full width)."""
        self.view_mode = "query"
        self._update_layout_for_tab()

    def action_show_tab_analysis(self) -> None:
        """Switch to AI Forensic Dossier tab (full width)."""
        self.view_mode = "analysis"
        self._update_layout_for_tab()

    def action_show_tab_video(self) -> None:
        """Switch to Carved Video ASCII Player tab."""
        self.view_mode = "video"
        self._update_layout_for_tab()
        self._render_video_frame()

    def action_show_tab_split(self) -> None:
        """Switch back to Split Multi-Panel (50/50 Query + AI Dossier)."""
        self.view_mode = "split"
        self._update_layout_for_tab()

    def action_toggle_maximize(self) -> None:
        """Toggle between Split Multi-Panel and maximized single-panel view."""
        if self.view_mode == "split":
            self.action_show_tab_query()
        else:
            self.action_show_tab_split()

    def _update_layout_for_tab(self) -> None:
        """Update widget visibility, width styling, and tab bar text according to view_mode."""
        self.query_one("#tab-bar", Static).update(self._get_tab_bar_text())
        q_panel = self.query_one("#query-results-panel", VerticalScroll)
        a_panel = self.query_one("#additional-analysis-panel", VerticalScroll)
        v_panel = self.query_one("#video-player-panel", Vertical)

        if self.view_mode == "split":
            q_panel.styles.display = "block"
            q_panel.styles.width = "50%"
            a_panel.styles.display = "block"
            a_panel.styles.width = "50%"
            v_panel.styles.display = "none"
            q_panel.focus()
        elif self.view_mode == "query":
            q_panel.styles.display = "block"
            q_panel.styles.width = "100%"
            a_panel.styles.display = "none"
            v_panel.styles.display = "none"
            q_panel.focus()
        elif self.view_mode == "analysis":
            q_panel.styles.display = "none"
            a_panel.styles.display = "block"
            a_panel.styles.width = "100%"
            v_panel.styles.display = "none"
            a_panel.focus()
        elif self.view_mode == "video":
            q_panel.styles.display = "none"
            a_panel.styles.display = "none"
            v_panel.styles.display = "block"
            v_panel.styles.width = "100%"
            v_panel.focus()

    def action_toggle_video_play(self) -> None:
        """Toggle play/pause state of the ASCII video player."""
        if self.playback_session is not None:
            self.playback_session.is_playing = not self.playback_session.is_playing
            self._render_video_frame()

    def action_video_seek_next(self) -> None:
        """Step 1 frame forward."""
        if self.playback_session is not None:
            self.playback_session.next_frame()
            self._render_video_frame()

    def action_video_seek_prev(self) -> None:
        """Step 1 frame backward."""
        if self.playback_session is not None:
            self.playback_session.prev_frame()
            self._render_video_frame()

    def action_video_seek_next_second(self) -> None:
        """Seek 1 second forward."""
        if self.playback_session is not None:
            step = max(1, int(self.playback_session.fps))
            self.playback_session.read_frame(self.playback_session.current_frame_idx + step)
            self._render_video_frame()

    def action_video_seek_prev_second(self) -> None:
        """Seek 1 second backward."""
        if self.playback_session is not None:
            step = max(1, int(self.playback_session.fps))
            self.playback_session.read_frame(self.playback_session.current_frame_idx - step)
            self._render_video_frame()

    def action_video_restart(self) -> None:
        """Restart video playback from beginning."""
        if self.playback_session is not None:
            self.playback_session.read_frame(0)
            self._render_video_frame()

    def action_video_toggle_mode(self) -> None:
        """Toggle between TrueColor half-blocks and monochrome ASCII characters."""
        if self.playback_session is not None:
            self.playback_session.color_mode = (
                "ascii" if self.playback_session.color_mode == "half_blocks" else "half_blocks"
            )
            self._render_video_frame()

    def action_next_plasma_pattern(self) -> None:
        """Cycle through the 15 live generative mathematical animation patterns."""
        try:
            widget = self.query_one("#plasma-widget", LivePlasmaWidget)
            widget.next_pattern()
        except Exception:
            pass

    def _on_playback_tick(self) -> None:
        """Timer callback advancing video playback when active."""
        if self.playback_session is not None and self.playback_session.is_playing:
            self.playback_session.next_frame()
            if self.view_mode in ("video", "split"):
                self._render_video_frame()

    def _render_video_frame(self) -> None:
        """Render current video frame into the ASCII video screen and status widgets."""
        if self.playback_session is None:
            return

        try:
            screen_widget = self.query_one("#ascii-video-screen", Static)
            status_widget = self.query_one("#ascii-video-status", Static)

            w = max(40, min(140, screen_widget.size.width or 80))
            h = max(12, min(40, screen_widget.size.height or 22))

            rendered_text = self.playback_session.render_current_ascii(width=w, height=h)
            screen_widget.update(rendered_text)

            status_line = self.playback_session.get_status_line()
            status_widget.update(
                f"[bold bright_cyan]{status_line}[/bold bright_cyan]\n"
                f"[dim]Controls: [SPACE] Play/Pause  [ [ / ] ] Seek 1s  [← / →] Step  [R] Restart  [M] Mode  [1-3,0] Switch Tabs[/dim]"
            )
        except Exception as exc:
            logger.debug(f"Render ASCII frame notice: {exc}")

    def action_switch_focus(self) -> None:
        focused = self.focused
        search_input = self.query_one("#search-input", PasteableInput)
        left_panel = self.query_one("#query-results-panel", VerticalScroll)
        right_panel = self.query_one("#additional-analysis-panel", VerticalScroll)
        video_panel = self.query_one("#video-player-panel", Vertical)

        if self.view_mode == "video":
            if focused == search_input:
                video_panel.focus()
            else:
                search_input.focus()
            return

        if focused == search_input:
            left_panel.focus()
        elif focused == left_panel:
            right_panel.focus()
        else:
            search_input.focus()

    def action_switch_focus_reverse(self) -> None:
        focused = self.focused
        search_input = self.query_one("#search-input", PasteableInput)
        left_panel = self.query_one("#query-results-panel", VerticalScroll)
        right_panel = self.query_one("#additional-analysis-panel", VerticalScroll)
        video_panel = self.query_one("#video-player-panel", Vertical)

        if self.view_mode == "video":
            if focused == video_panel:
                search_input.focus()
            else:
                video_panel.focus()
            return

        if focused == search_input:
            right_panel.focus()
        elif focused == right_panel:
            left_panel.focus()
        else:
            search_input.focus()

    def action_clear_or_focus_search(self) -> None:
        """Clear search input or return from single tab to split view."""
        search_input = self.query_one("#search-input", PasteableInput)
        if self.view_mode != "split":
            self.action_show_tab_split()
        elif self.focused == search_input:
            search_input.value = ""
        else:
            search_input.focus()

    def action_new_file(self) -> None:
        """Reset to evidence file ingestion mode to upload and analyze another file."""
        self.mode = "file"
        self.engine.clear()
        search_input = self.query_one("#search-input", PasteableInput)
        search_input.value = ""
        search_input.placeholder = "Enter evidence / video file path..."
        search_input.focus()
        self.query_one("#query-results-content", Static).update(self._get_file_prompt_text())
        self.query_one("#additional-analysis-content", Static).update(self._get_initial_analysis_placeholder_text())
        self.query_one("#query-results-panel", VerticalScroll).scroll_home(animate=False)
        self.query_one("#additional-analysis-panel", VerticalScroll).scroll_home(animate=False)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.action_submit_input()

    def action_submit_input(self) -> None:
        """Handle user input: either file upload or conversational query analysis."""
        search_input = self.query_one("#search-input", PasteableInput)
        val = search_input.value.strip()

        if not val:
            return

        # Check for explicit file reset command
        if val.startswith(":file ") or val.startswith(":load "):
            new_file = val.split(" ", 1)[1].strip()
            self._start_file_ingestion(new_file)
            return
        elif val == ":reset":
            self.mode = "file"
            search_input.value = ""
            search_input.placeholder = "Enter evidence / video file path..."
            self.query_one("#query-results-content", Static).update(self._get_file_prompt_text())
            self.query_one("#additional-analysis-content", Static).update(self._get_initial_analysis_placeholder_text())
            return

        if self.mode == "file":
            self._start_file_ingestion(val)
        else:
            self._start_query_analysis(val)

    def _start_file_ingestion(self, file_path_str: str) -> None:
        """Validate file and start background pipeline worker."""
        clean_str = clean_pasted_path(file_path_str)
        path = Path(clean_str).expanduser().resolve()
        if not path.is_file():
            results_content = self.query_one("#query-results-content", Static)
            lines = [
                f"[bold red]❌ File not found:[/bold red] [yellow]{path}[/yellow]",
                _rule(48),
                "",
                "Please verify the file path exists and try again.",
            ]
            results_content.update("\n".join(lines))
            return

        results_content = self.query_one("#query-results-content", Static)
        lines = [
            f"[bold white]Ingesting Evidence File:[/bold white] [cyan]{path.name}[/cyan]",
            f"[dim]Path: {path} ({human_size(path.stat().st_size)})[/dim]",
            _rule(48),
            "",
            "[bold yellow]⚡ Running TraceX Forensic Analysis Pipeline...[/bold yellow]",
            "[dim]Detect -> Parse -> Extract -> Vision & Motion -> Integrity Analysis[/dim]",
            "",
            "[bold white]Live Progress:[/bold white]",
        ]
        results_content.update("\n".join(lines))

        analysis_content = self.query_one("#additional-analysis-content", Static)
        lines_right = [
            "[bold yellow]⚡ Processing evidence...[/bold yellow]",
            _rule(48),
            "",
            "Extracting video streams and computing forensic telemetry.",
            "The full analysis dossier will populate automatically upon completion.",
        ]
        analysis_content.update("\n".join(lines_right))

        self._run_pipeline_worker(str(path))

    @work(exclusive=True, thread=True)
    def _run_pipeline_worker(self, file_path_str: str) -> None:
        """Worker thread executing the real pipeline."""
        try:
            def update_progress(msg: str):
                self.call_from_thread(self._on_pipeline_progress, msg)

            res = self.engine.run_pipeline(file_path_str, progress_cb=update_progress)
            self.call_from_thread(self._on_pipeline_success, res)
        except Exception as exc:
            self.call_from_thread(self._on_pipeline_error, file_path_str, str(exc))

    def _on_pipeline_progress(self, msg: str) -> None:
        results_content = self.query_one("#query-results-content", Static)
        existing = str(results_content.render())
        results_content.update(f"{existing}\n• [dim]{msg}[/dim]")

    def _on_pipeline_success(self, res: PipelineResult) -> None:
        """Switch to Query Analysis mode and render full AI analysis dossier in Right Panel."""
        self.mode = "query"

        # Update Right Panel: Full AI analysis dossier from the original CLI
        right_text = self._format_ai_analysis_dossier(res)
        analysis_scroll = self.query_one("#additional-analysis-panel", VerticalScroll)
        self.query_one("#additional-analysis-content", Static).update(right_text)
        analysis_scroll.scroll_home(animate=False)

        # Update Left Panel: Ready for Query Analysis
        left_text = self._format_pipeline_completion(res)
        query_scroll = self.query_one("#query-results-panel", VerticalScroll)
        self.query_one("#query-results-content", Static).update(left_text)
        query_scroll.scroll_home(animate=False)

        # Update Search Bar prompt to Query Analysis
        search_input = self.query_one("#search-input", PasteableInput)
        search_input.value = ""
        search_input.placeholder = "Ask about this video timeline... (type ':file <path>' to switch files)"
        search_input.focus()

        # Initialize ASCII Video Player with carved video or source evidence
        video_target = None
        if res.recovered_recordings:
            first_rec = res.recovered_recordings[0]
            if isinstance(first_rec, dict):
                ep = first_rec.get("extracted_path") or first_rec.get("file_path")
            elif isinstance(first_rec, (list, tuple)) and len(first_rec) > 3:
                ep = first_rec[3]
            else:
                ep = None
            if ep and Path(ep).is_file():
                video_target = Path(ep)

        if not video_target and res.file_path and res.file_path.is_file():
            video_target = res.file_path

        if video_target:
            if self.playback_session is not None:
                self.playback_session.close()
            self.playback_session = VideoPlaybackSession(video_target)
            self._render_video_frame()

        # If an initial query was queued, run it
        if self.initial_query:
            q = self.initial_query
            self.initial_query = None
            search_input.value = q
            self.action_submit_input()

    def _on_pipeline_error(self, file_str: str, err: str) -> None:
        results_content = self.query_one("#query-results-content", Static)
        lines = [
            f"[bold red]❌ Pipeline Error on file:[/bold red] {file_str}",
            _rule(48),
            "",
            f"[bold yellow]Details:[/bold yellow] {err}",
            "",
            "[dim]Please check the path or enter another file below.[/dim]",
        ]
        results_content.update("\n".join(lines))
        self.query_one("#additional-analysis-content", Static).update(
            f"[bold red]Pipeline execution failed on evidence:[/bold red]\n{file_str}\n\n"
            f"[yellow]{err}[/yellow]"
        )
        self.query_one("#search-input", PasteableInput).focus()

    def _start_query_analysis(self, query_text: str) -> None:
        """Run conversational Q&A on the loaded video events."""
        results_content = self.query_one("#query-results-content", Static)
        lines = [
            f"[bold bright_cyan]Query:[/bold bright_cyan] [bold white]\"{query_text}\"[/bold white]",
            _rule(48),
            "",
            "[bold yellow]⚡ Querying TraceX AI model over event timeline...[/bold yellow]",
        ]
        results_content.update("\n".join(lines))
        self._run_query_worker(query_text)

    @work(exclusive=True, thread=True)
    def _run_query_worker(self, query_text: str) -> None:
        """Worker thread executing Groq conversational Q&A."""
        try:
            ans: QueryAnswer = self.engine.ask_video_query(query_text)
            self.call_from_thread(self._on_query_success, ans)
        except Exception as exc:
            self.call_from_thread(self._on_query_error, query_text, str(exc))

    def _on_query_success(self, ans: QueryAnswer) -> None:
        formatted = self._format_query_answer(ans)
        query_panel = self.query_one("#query-results-panel", VerticalScroll)
        self.query_one("#query-results-content", Static).update(formatted)
        query_panel.scroll_home(animate=False)
        search_input = self.query_one("#search-input", PasteableInput)
        search_input.value = ""
        search_input.focus()

    def _on_query_error(self, query_text: str, err: str) -> None:
        results_content = self.query_one("#query-results-content", Static)
        lines = [
            "[bold red]❌ Query Analysis Error[/bold red]",
            _rule(48),
            "",
            f"[bold white]Query:[/bold white] {query_text}",
            f"[bold yellow]Details:[/bold yellow] {err}",
            "",
            "[dim]You can type another question below, or ':file <path>' to load a new file.[/dim]",
        ]
        results_content.update("\n".join(lines))
        self.query_one("#search-input", PasteableInput).focus()

    def _format_pipeline_completion(self, res: PipelineResult) -> str:
        lines = [
            "[bold green]✔ Evidence Ingested Successfully[/bold green]",
            _rule(48),
            "",
            f"• [bold white]File:[/bold white] [cyan]{res.file_path.name}[/cyan] [dim]({human_size(res.file_size)})[/dim]",
            f"• [bold white]Detected Vendor:[/bold white] {res.vendor_name} [dim]({res.vendor_confidence * 100:.0f}% confidence)[/dim]",
            f"• [bold white]Pipeline Duration:[/bold white] {res.duration_seconds:.2f}s",
            "",
            "[bold bright_cyan]AI Forensic Analysis Dossier Loaded[/bold bright_cyan]",
            "The complete forensic analysis report is rendered in the [bold cyan]AI FORENSIC ANALYSIS[/bold cyan] panel on the right.",
            "It includes all discovered recordings, complete events summary, event reconstruction,",
            "forensic summary, tampering and integrity checks, and object disappearances.",
            "",
            _rule(48),
            "[bold bright_white]Query Analysis Ready[/bold bright_white]",
            "",
            "Enter questions about this video in the query bar below to query the AI model.",
            "",
            "[bold white]Suggested Queries:[/bold white]",
            "  • [cyan]was there any collision or vehicle impact?[/cyan]",
            "  • [cyan]what vehicles or objects were involved?[/cyan]",
            "  • [cyan]summarize what happened in this video[/cyan]",
            "  • [cyan]when was the highest motion activity observed?[/cyan]",
            "",
            "[dim]Press [bold #58a6ff]Ctrl+O[/bold #58a6ff] (or type ':file <path>') anytime to upload another file.[/dim]",
        ]
        return "\n".join(lines)

    def _format_query_answer(self, ans: QueryAnswer) -> str:
        lines = [
            f"[bold bright_cyan]Query:[/bold bright_cyan] [bold bright_white]\"{ans.query}\"[/bold bright_white]",
            f"[dim]Engine: {ans.source} • Latency: {ans.duration_seconds:.2f}s[/dim]",
            _rule(48),
            "",
            "[bold underline bright_white]Findings & Analysis[/bold underline bright_white]",
            f"{ans.answer}",
            "",
        ]

        if ans.matching_events:
            lines.append(f"[bold underline bright_white]Matching Timeline Events ({len(ans.matching_events)} records)[/bold underline bright_white]")
            lines.append(f"{'CAMERA':<10} {'EVENT TYPE':<22} {'OBJECT':<14} {'TIMESTAMP':<20} {'CONF'}")
            lines.append(_rule(72))
            for ev in ans.matching_events:
                cam = str(ev.get("camera_id", "-"))[:8]
                e_type = str(ev.get("event_type", "-"))[:20]
                obj = str(ev.get("object_type", "-"))[:12]
                st = str(ev.get("start_time", "-"))[:19]
                conf = ev.get("confidence")
                conf_s = f"{conf:.2f}" if isinstance(conf, (int, float)) else "-"
                lines.append(f"{cam:<10} [cyan]{e_type:<22}[/cyan] [white]{obj:<14}[/white] [dim]{st:<20}[/dim] {conf_s}")

        lines.append("")
        lines.append("[dim]Ask another question below, or press [bold #58a6ff]Ctrl+O[/bold #58a6ff] to upload another file.[/dim]")
        return "\n".join(lines)

    def _format_ai_analysis_dossier(self, res: PipelineResult) -> str:
        """Format the executive-grade AI forensic analysis dossier with pipeline telemetry and object frequency counts."""
        from backend.core.search.context_compressor import compress_events_into_track_spans

        lines = []

        # -----------------------------------------------------
        # 1. PIPELINE ARCHITECTURE & EVIDENCE FLOW
        # -----------------------------------------------------
        lines.append(_section_header("TraceX Forensic Pipeline Architecture & Evidence Flow"))
        lines.append(f"• [bold white]Evidence File:[/bold white]   {res.file_path}")
        lines.append(f"• [bold white]File Size:[/bold white]       [cyan]{human_size(res.file_size)}[/cyan] [dim]({res.file_size:,} bytes)[/dim]")
        lines.append(f"• [bold white]Detected DVR:[/bold white]    [bold green]{res.vendor_name.upper()}[/bold green] [dim](Confidence: {res.vendor_confidence * 100:.1f}%)[/dim]")
        lines.append("")
        lines.append("[bold white]Pipeline Processing Stages:[/bold white]")
        lines.append("  [bold green]✔ Stage 1 (Carving & Ingestion):[/bold green]    Carved playable H.264/MP4 stream without modifying source evidence.")
        lines.append("  [bold green]✔ Stage 2 (CCTV Preprocessing):[/bold green]    Applied adaptive LAB CLAHE, auto-gamma correction, and unsharp filter.")
        lines.append("  [bold green]✔ Stage 3 (AI & Motion Engine):[/bold green]    Pure OpenCV HOG + MOG2 Morphometrics (0 hallucinated COCO classes).")
        lines.append("  [bold green]✔ Stage 4 (Event Reconstruction):[/bold green]  8-point compass trajectory tracking and localized perimeter loitering analysis.")
        lines.append("")

        # -----------------------------------------------------
        # 2. DISCOVERED RECORDINGS & STREAMS
        # -----------------------------------------------------
        lines.append(_section_header("Discovered Recordings & Extracted Streams", f"{len(res.recovered_recordings)} carved"))
        if res.recovered_recordings:
            lines.append(f"{'RECORDING ID':<24} {'CAMERA':<10} {'STATUS':<12} {'CARVED FILE'}")
            lines.append(_rule(72))
            for item in res.recovered_recordings:
                if isinstance(item, dict):
                    r_id = str(item.get("recording_id", "-"))[:22]
                    c_id = str(item.get("camera_id", "-"))[:8]
                    st = str(item.get("status", "-"))[:10]
                    ep = item.get("extracted_path") or item.get("file_path") or ""
                    fname = Path(ep).name if ep else "-"
                elif isinstance(item, (list, tuple)):
                    r_id = str(item[0])[:22]
                    c_id = str(item[1])[:8] if len(item) > 1 else "-"
                    st = str(item[2])[:10] if len(item) > 2 else "-"
                    fname = Path(item[3]).name if len(item) > 3 and item[3] else "-"
                else:
                    continue
                lines.append(f"[cyan]{r_id:<24}[/cyan] [white]{c_id:<10}[/white] [green]{st:<12}[/green] [dim]{fname}[/dim]")
        else:
            lines.append("[dim]No video streams were carved or extracted.[/dim]")
        lines.append("")

        # -----------------------------------------------------
        # 3. OBJECT DETECTION FREQUENCY & DISTRIBUTION (NO FRAME DUMPING!)
        # -----------------------------------------------------
        lines.append(_section_header("AI Object Detection Frequency & Distribution", f"{len(res.events)} total detections"))
        if res.events:
            # Aggregate detection frequency by class
            class_counts: dict[str, int] = {}
            class_tracks: dict[str, set[Any]] = {}
            class_first_seen: dict[str, datetime] = {}
            class_last_seen: dict[str, datetime] = {}

            for cam, ev in res.events:
                obj = str(getattr(ev, "object_type", "-") or getattr(ev, "event_type", "-") or "motion").lower()
                if obj in {"none", "unknown", ""}:
                    obj = "motion"

                class_counts[obj] = class_counts.get(obj, 0) + 1
                tid = getattr(ev, "track_id", None)
                if tid is not None:
                    class_tracks.setdefault(obj, set()).add(tid)

                st = getattr(ev, "start_time", None)
                if st and hasattr(st, "isoformat"):
                    if obj not in class_first_seen or st < class_first_seen[obj]:
                        class_first_seen[obj] = st
                    if obj not in class_last_seen or st > class_last_seen[obj]:
                        class_last_seen[obj] = st

            total_dets = max(1, len(res.events))
            lines.append(f"{'OBJECT CLASS':<18} {'DETECTIONS':<14} {'UNIQUE TRACKS':<16} {'TIMELINE SPAN':<24} {'FREQUENCY %'}")
            lines.append(_rule(86))

            for obj, count in sorted(class_counts.items(), key=lambda x: x[1], reverse=True):
                tracks_count = len(class_tracks.get(obj, set()))
                tracks_s = f"{tracks_count} entity(s)" if tracks_count > 0 else "-"
                pct = (count / total_dets) * 100

                st = class_first_seen.get(obj)
                et = class_last_seen.get(obj)
                if st and et:
                    st_str = st.isoformat(sep=" ", timespec="seconds")[11:]
                    et_str = et.isoformat(sep=" ", timespec="seconds")[11:]
                    span_s = f"{st_str} → {et_str}"
                else:
                    span_s = "Full timeline"

                lines.append(
                    f"[bold white]{obj.capitalize():<18}[/bold white] "
                    f"[cyan]{count:<14}[/cyan] "
                    f"[white]{tracks_s:<16}[/white] "
                    f"[dim]{span_s:<24}[/dim] "
                    f"[bold green]{pct:.1f}%[/bold green]"
                )
        else:
            lines.append("[yellow]No AI events detected across any recording.[/yellow]")
        lines.append("")

        # -----------------------------------------------------
        # 4. EXECUTIVE FORENSIC SUMMARY
        # -----------------------------------------------------
        lines.append(_section_header("Executive AI Forensic Summary"))
        if res.summaries:
            for s_idx, s in enumerate(res.summaries, start=1):
                headline = getattr(s, "headline", None)
                sum_text = getattr(s, "summary", None)
                evt_count = getattr(s, "event_count", None)
                objs = getattr(s, "objects_detected", None)
                st = getattr(s, "start_time", None)
                et = getattr(s, "end_time", None)
                key_events = getattr(s, "key_events", None) or []
                meta = getattr(s, "metadata", {}) or {}
                conf_label = meta.get("confidence_label", "HIGH (100% Deterministic)")

                if len(res.summaries) > 1:
                    lines.append(f"[bold cyan]Camera Stream #{s_idx}:[/bold cyan]")
                if headline:
                    lines.append(f"• [bold bright_yellow]INCIDENT / ACTIVITY:[/bold bright_yellow] {headline}")
                if sum_text:
                    lines.append(f"• [bold bright_cyan]FORENSIC SUMMARY:[/bold bright_cyan] {sum_text}")

                lines.append(f"• [bold white]Time Window:[/bold white]          [dim]{st or 'unknown'}[/dim] → [dim]{et or 'unknown'}[/dim]")
                lines.append(f"• [bold white]Events Reconstructed:[/bold white] [cyan]{evt_count or len(res.reconstructed_events)}[/cyan]")
                if objs:
                    objs_s = ", ".join(objs) if isinstance(objs, (list, tuple, set)) else str(objs)
                    lines.append(f"• [bold white]Objects Detected:[/bold white]     [white]{objs_s}[/white]")
                lines.append(f"• [bold white]Reconstruction Conf.:[/bold white] [bold green]{conf_label}[/bold green]")

                if key_events:
                    lines.append("• [bold white]Key Forensic Milestones:[/bold white]")
                    for k_idx, kev in enumerate(key_events[:5], start=1):
                        lines.append(f"    {k_idx}. {kev}")
                lines.append("")
        else:
            lines.append("[dim]No forensic summary generated.[/dim]")
            lines.append("")

        # -----------------------------------------------------
        # 5. CRITICAL FORENSIC ALERTS & RECONSTRUCTION
        # -----------------------------------------------------
        loiter_alerts = [
            e for e in res.reconstructed_events
            if "LOITER" in str(getattr(e, "event_type", "")).upper()
        ]
        sudden_alerts = [
            e for e in res.reconstructed_events
            if "SUDDEN" in str(getattr(e, "event_type", "")).upper()
        ]

        if loiter_alerts or sudden_alerts:
            lines.append(_section_header("Critical Forensic Observations & Alerts", f"{len(loiter_alerts) + len(sudden_alerts)} alerts"))
            for alert in (loiter_alerts + sudden_alerts)[:6]:
                title = getattr(alert, "title", None) or getattr(alert, "event_type", "Alert")
                desc = getattr(alert, "description", "")
                st = getattr(alert, "start_time", None)
                st_s = st.isoformat(sep=" ", timespec="seconds") if st and hasattr(st, "isoformat") else ""
                lines.append(f"• [bold yellow]⚠ {title}[/bold yellow] [dim]({st_s})[/dim]")
                if desc:
                    lines.append(f"  [white]{desc}[/white]")
            if len(loiter_alerts) + len(sudden_alerts) > 6:
                lines.append(f"[dim]... and {len(loiter_alerts) + len(sudden_alerts) - 6} additional critical observations ...[/dim]")
            lines.append("")

        # -----------------------------------------------------
        # 6. TRACKED ENTITY TRAJECTORY TIMELINE (TOP TRACKS)
        # -----------------------------------------------------
        spans = compress_events_into_track_spans(res.events)
        lines.append(_section_header("Tracked Entity Trajectory Timeline", f"{len(spans)} distinct entities"))

        if spans:
            lines.append(f"{'TRACK':<8} {'CLASS':<12} {'FIRST SEEN → LAST SEEN':<24} {'DURATION':<10} {'HEADING':<18} {'AVG SPEED':<12} {'BEHAVIOR'}")
            lines.append(_rule(98))
            display_spans = spans[:12]
            for s in display_spans:
                st_str = s.start_time.isoformat(sep=" ", timespec="seconds")[11:]
                et_str = s.end_time.isoformat(sep=" ", timespec="seconds")[11:]
                span_str = f"{st_str} → {et_str}"
                status_tag = "[bold yellow]⚠ LOITERING[/bold yellow]" if s.is_loitering else "[dim]Normal Transit[/dim]"
                speed_str = f"{s.avg_speed:.1f} px/s" if s.avg_speed > 0 else "0.0 px/s"

                lines.append(
                    f"[cyan]#{s.track_id:<7}[/cyan] "
                    f"[white]{s.object_type.capitalize():<12}[/white] "
                    f"[dim]{span_str:<24}[/dim] "
                    f"{s.duration_seconds:.1f}s{'':<5} "
                    f"{s.direction:<18} "
                    f"{speed_str:<12} "
                    f"{status_tag}"
                )
            if len(spans) > len(display_spans):
                lines.append(f"[dim]... + {len(spans) - len(display_spans)} additional tracked entities summarized ...[/dim]")
        else:
            lines.append("[dim]No persistent entity trajectories tracked.[/dim]")
        lines.append("")

        # -----------------------------------------------------
        # 7. TAMPERING / VIDEO INTEGRITY CHECKS (FULL METRICS)
        # -----------------------------------------------------
        lines.append(_section_header("Tampering & Video Stream Integrity", f"{len(res.integrity_results)} checks"))
        if res.integrity_results:
            for r_id, integ in res.integrity_results:
                tc = "[green]✔ Pass[/green]" if integ.get("timestamp_continuity") else "[red]▲ Review[/red]"
                fc = "[green]✔ Pass[/green]" if integ.get("frame_continuity") else "[red]▲ Review[/red]"
                fps_c = "[green]✔ Pass[/green]" if integ.get("fps_consistency") else "[red]▲ Review[/red]"
                df_c = "[green]✔ Pass[/green]" if integ.get("duplicate_frames") else "[yellow]▲ Review[/yellow]"
                mc = "[green]✔ Pass[/green]" if integ.get("metadata_consistency", True) else "[red]▲ Review[/red]"
                rc = "[green]✔ Pass[/green]" if integ.get("resolution_consistency", True) else "[red]▲ Review[/red]"
                cc = "[green]✔ Pass[/green]" if integ.get("compression_consistency", True) else "[red]▲ Review[/red]"
                fc_count = integ.get("frames_checked", 0)

                lines.append(f"[bold cyan]Recording: {r_id}[/bold cyan]")
                lines.append(f"  • Timestamp Continuity:  {tc} [dim](Gaps: {integ.get('timestamp_gaps', 0)})[/dim]")
                lines.append(f"  • Frame Continuity:      {fc} [dim](Corrupted: {integ.get('corrupted_frames', 0)})[/dim]")
                lines.append(f"  • FPS Consistency:       {fps_c}")
                lines.append(f"  • Duplicate Sequences:   {df_c} [dim](Count: {integ.get('duplicate_sequences', 0)})[/dim]")
                lines.append(f"  • Metadata / Resolution: {mc} / {rc}")
                lines.append(f"  • Compression Stability: {cc} [dim]({fc_count} frames checked)[/dim]")

                details = integ.get("details", {})
                if details:
                    meta_str = details.get("metadata") or details.get("observed_fps") or ""
                    if meta_str:
                        lines.append(f"  • Stream Specs:          [dim]{meta_str}[/dim]")

                anomalies = integ.get("anomalies", [])
                if anomalies:
                    lines.append("  [bold red]Detected Anomalies:[/bold red]")
                    for a in anomalies[:4]:
                        lines.append(f"    ▲ [yellow]{a}[/yellow]")
                    if len(anomalies) > 4:
                        lines.append(f"    [dim]... + {len(anomalies) - 4} more frame sequence anomalies ...[/dim]")
                else:
                    lines.append("  • [green]✔ No video manipulation or tampering anomalies detected.[/green]")
                lines.append("")
        else:
            lines.append("[dim]No playable recordings available for integrity analysis.[/dim]\n")

        # -----------------------------------------------------
        # 8. OBJECT DISAPPEARANCE DETECTION
        # -----------------------------------------------------
        lines.append(_section_header("Object Disappearance & Continuity", f"{len(res.disappearance_results)} flags"))
        if res.disappearance_results:
            for cand in res.disappearance_results:
                cam = cand.get("camera_id", "-")
                obj = cand.get("object_type", "-")
                st = cand.get("first_seen", "-")
                et = cand.get("last_seen", "-")
                obs = cand.get("observations_count", "-")
                note = cand.get("note", "")

                lines.append(f"• [yellow][REVIEW FLAG][/yellow] Camera {cam}: [bold white]{obj.upper()}[/bold white]")
                lines.append(f"  First Seen: {st} | Last Seen: {et} | Observations: {obs}")
                if note:
                    lines.append(f"  Note: {note}")
        else:
            lines.append("[green]✔ No suspicious object disappearance anomalies detected.[/green]")

        # -----------------------------------------------------
        # 9. WARNINGS AND ERRORS (IF ANY)
        # -----------------------------------------------------
        if res.warnings:
            lines.append("")
            lines.append(_section_header("Pipeline Warnings", f"{len(res.warnings)} alerts"))
            for w in res.warnings:
                lines.append(f"• [yellow]{w}[/yellow]")

        if res.errors:
            lines.append("")
            lines.append(_section_header("Pipeline Extraction Errors", f"{len(res.errors)} errors"))
            for err in res.errors:
                lines.append(f"• [red]{err}[/red]")

        return "\n".join(lines)


def run_tui(default_file_path: str | None = None, initial_query: str | None = None) -> None:
    """Launch the TraceX Full-Screen TUI."""
    app = TraceXApp(default_file_path=default_file_path, initial_query=initial_query)
    app.run()


if __name__ == "__main__":
    run_tui()
