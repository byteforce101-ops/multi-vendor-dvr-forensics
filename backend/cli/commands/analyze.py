"""dvrforensics analyze VIDEO_PATH"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import typer
from rich.table import Table

from backend.cli.common import require_file
from backend.cli.exit_codes import ExitCode
from backend.cli.theme import error, get_console, section_header, success, warn

DEFAULT_MODEL = "yolo26n.pt"


def analyze(
    video_path: Path = typer.Argument(..., help="Path to the video file to analyze"),
    output: Optional[Path] = typer.Option(
        None, "--output", help="[reserved] Where to write analysis artifacts; currently events are only printed"
    ),
    sample_fps: float = typer.Option(2.0, "--sample-fps", help="Frames per second to sample for analysis"),
    model: str = typer.Option(DEFAULT_MODEL, "--model", help="Path to the YOLO model weights"),
    start_time: Optional[datetime] = typer.Option(
        None,
        "--start-time",
        help="Recording start time (ISO 8601), used to convert frame offsets to absolute timestamps. "
        "Defaults to now if omitted.",
    ),
) -> None:
    """Run the existing video analysis pipeline (motion + YOLO + tracking + events) on a video file."""
    console = get_console()
    section_header(console, "Analyze")

    resolved = require_file(video_path, console)

    try:
        from backend.video.analysis.service import VideoAnalysisService
    except ImportError as exc:
        error(console, f"Video analysis requires optional AI dependencies that aren't installed: {exc}")
        console.print("[dim]Install them with: pip install ultralytics av[/dim]")
        raise typer.Exit(code=ExitCode.MISSING_DEPENDENCY)

    video_start = start_time or datetime.now(timezone.utc)

    console.print(f"[field]Video:[/field] [path]{resolved}[/path]")
    console.print(f"[field]Model:[/field] {model}")
    console.print(f"[field]Sample FPS:[/field] {sample_fps}")
    console.print(f"[field]Start time:[/field] {video_start.isoformat()}\n")

    try:
        service = VideoAnalysisService(yolo_model=model)
    except Exception as exc:  # model file missing / ultralytics not installed / etc.
        error(console, f"Could not initialize the AI pipeline: {exc}")
        raise typer.Exit(code=ExitCode.MISSING_DEPENDENCY)

    with console.status("[brand]Running AI pipeline (probe → frames → motion → YOLO → events)...[/brand]", spinner="arc"):
        try:
            result = service.analyze(
                video_id=resolved.stem,
                camera_id="CH-CLI",
                video_path=resolved,
                video_start_time=video_start,
                frame_sample_fps=sample_fps,
            )
        except FileNotFoundError as exc:
            error(console, str(exc))
            raise typer.Exit(code=ExitCode.FILE_NOT_FOUND)
        except Exception as exc:
            error(console, f"Video analysis failed: {exc}")
            raise typer.Exit(code=ExitCode.GENERAL_ERROR)

    console.print(
        f"[field]Frames analyzed:[/field] {result.frame_count_analyzed}   "
        f"[field]Duration:[/field] {result.metadata.duration_seconds or 0:.1f}s   "
        f"[field]Resolution:[/field] {result.metadata.width}x{result.metadata.height}\n"
    )

    if not result.events:
        warn(console, "No events were detected.")
        return

    table = Table(border_style="brand.dim", header_style="brand", title=f"{len(result.events)} event(s)")
    table.add_column("Type")
    table.add_column("Object")
    table.add_column("Start")
    table.add_column("End")
    table.add_column("Confidence")
    table.add_column("Track ID")

    for e in result.events:
        table.add_row(
            e.event_type,
            e.object_type or "[dim]-[/dim]",
            e.start_time.isoformat(sep=" ", timespec="seconds"),
            e.end_time.isoformat(sep=" ", timespec="seconds"),
            f"{e.confidence:.2f}" if e.confidence is not None else "[dim]-[/dim]",
            str(e.track_id) if e.track_id is not None else "[dim]-[/dim]",
        )

    console.print(table)
    success(console, f"Analysis complete — {len(result.events)} event(s) found.")
    if output:
        warn(console, "--output is reserved for a future artifact-writing mode; results were printed above only.")
