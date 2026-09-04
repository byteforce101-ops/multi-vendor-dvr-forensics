"""Visual theme for the dvrforensics CLI.

Everything cosmetic lives here so command modules stay thin and forensic
logic never gets tangled up with presentation. Animations here are either
(a) tied to real work (progress bars driven by actual bytes/records
processed) or (b) short, skippable flourishes that never block or slow
down a command's actual output. Animations are automatically skipped when
stdout isn't an interactive terminal (piped/redirected/CI) so scripting
against the CLI is never affected.
"""

from __future__ import annotations

import os
import sys
import time

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.theme import Theme

_THEME = Theme(
    {
        "brand": "bold spring_green3",
        "brand.dim": "spring_green4",
        "dim": "grey58",
        "warn": "bold gold3",
        "err": "bold red3",
        "ok": "bold green3",
        "path": "italic bright_cyan",
        "field": "bold white",
        "rec": "bold red3",
    }
)

_console: Console | None = None


def get_console() -> Console:
    global _console
    if _console is None:
        if sys.platform == "win32":
            try:
                sys.stdout.reconfigure(encoding="utf-8", errors="replace")
                sys.stderr.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass
        kwargs: dict = {"theme": _THEME, "highlight": False}
        if not sys.stdout.isatty():
            # Rich's non-terminal fallback width (80) is too narrow for our
            # wider tables (case/evidence lists) and truncates content when
            # output is piped, redirected, or captured by tests. Real
            # interactive terminals are left alone (auto-detected as usual).
            kwargs["width"] = 120
        _console = Console(**kwargs)
    return _console


def animations_enabled(console: Console) -> bool:
    if os.environ.get("DVRFORENSICS_NO_ANIMATION"):
        return False
    if os.environ.get("NO_COLOR"):
        return False
    return console.is_terminal


# ---------------------------------------------------------------------------
# Banner
# ---------------------------------------------------------------------------

_DVR_BLOCK = r"""
 ██████╗ ██╗   ██╗██████╗
 ██╔══██╗██║   ██║██╔══██╗
 ██║  ██║██║   ██║██████╔╝
 ██║  ██║╚██╗ ██╔╝██╔══██╗
 ██████╔╝ ╚████╔╝ ██║  ██║
 ╚═════╝   ╚═══╝  ╚═╝  ╚═╝
""".strip("\n")

_TAGLINE = "F O R E N S I C S   P L A T F O R M"
_SUBTITLE = "chain-of-custody \u00b7 offline-first \u00b7 local evidence, local disk"


def print_banner(console: Console | None = None, *, animate: bool = True) -> None:
    console = console or get_console()

    if animate and animations_enabled(console):
        frames = ["\u25cb REC", "\u25cf REC", "\u25cb REC", "\u25cf REC", "\u25cb REC", "\u25cf REC"]
        with console.status("", spinner="dots") as status:
            for frame in frames:
                status.update(f"[rec]{frame}[/rec]  [dim]initializing evidence session...[/dim]")
                time.sleep(0.09)

    body = Text(_DVR_BLOCK, style="brand")
    body.append("\n\n")
    body.append(_TAGLINE, style="brand.dim")
    body.append("\n")
    body.append(_SUBTITLE, style="dim")

    console.print(Panel(body, border_style="brand", expand=False, padding=(1, 4)))


# ---------------------------------------------------------------------------
# Section headers / messages
# ---------------------------------------------------------------------------

def section_header(console: Console, title: str, icon: str = "\u25b8") -> None:
    console.print(f"\n[brand]{icon} {title.upper()}[/brand]")
    console.print("[brand.dim]" + "\u2500" * (len(title) + 2) + "[/brand.dim]")


def success(console: Console, message: str) -> None:
    console.print(f"[ok]\u2713[/ok] {message}")


def warn(console: Console, message: str) -> None:
    console.print(f"[warn]\u26a0[/warn]  {message}")


def error(console: Console, message: str) -> None:
    console.print(f"[err]\u2717[/err] {message}")


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def human_size(num_bytes: int) -> str:
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB", "PB"):
        if size < 1024.0:
            return f"{size:.2f} {unit}" if unit != "B" else f"{int(size)} {unit}"
        size /= 1024.0
    return f"{size:.2f} EB"


def fact_table() -> Table:
    """A borderless two-column grid for key/value facts, used across commands."""
    table = Table.grid(padding=(0, 2))
    table.add_column(justify="right")
    table.add_column()
    return table
