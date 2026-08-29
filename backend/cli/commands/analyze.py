"""dvrforensics analyze VIDEO_PATH"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import typer
from rich.panel import Panel
from rich.table import Table

from backend.cli.common import require_file
from backend.cli.exit_codes import ExitCode
from backend.cli.theme import (
    error,
    get_console,
    section_header,
    success,
    warn,
)

DEFAULT_MODEL = "yolo26n.pt"


def _print_reconstructed_events(console, result) -> None:
    """
    Display AI forensic event reconstruction results.

    Uses getattr() so the CLI remains compatible if a result
    object does not contain the new reconstruction fields yet.
    """

    reconstructed = getattr(
        result,
        "reconstructed_events",
        None,
    )

    section_header(
        console,
        "AI Forensic Event Reconstruction",
    )

    if not reconstructed:
        warn(
            console,
            "No higher-level forensic activities were reconstructed.",
        )
        return

    table = Table(
        border_style="brand.dim",
        header_style="brand",
        title=f"{len(reconstructed)} reconstructed activity(s)",
    )

    table.add_column(
        "Type",
        style="brand",
    )

    table.add_column(
        "Activity",
    )

    table.add_column(
        "Start",
    )

    table.add_column(
        "End",
    )

    table.add_column(
        "Objects",
    )

    table.add_column(
        "Confidence",
    )

    for event in reconstructed:

        event_type = getattr(
            event,
            "event_type",
            "UNKNOWN",
        )

        title = getattr(
            event,
            "title",
            None,
        ) or event_type

        start_time = getattr(
            event,
            "start_time",
            None,
        )

        end_time = getattr(
            event,
            "end_time",
            None,
        )

        objects = getattr(
            event,
            "objects",
            None,
        )

        confidence = getattr(
            event,
            "confidence",
            None,
        )

        if isinstance(objects, (list, tuple, set)):
            objects_text = ", ".join(
                str(item)
                for item in objects
            )
        else:
            objects_text = (
                str(objects)
                if objects
                else "-"
            )

        if start_time:
            start_text = start_time.isoformat(
                sep=" ",
                timespec="seconds",
            )
        else:
            start_text = "-"

        if end_time:
            end_text = end_time.isoformat(
                sep=" ",
                timespec="seconds",
            )
        else:
            end_text = "-"

        confidence_text = (
            f"{confidence:.2f}"
            if isinstance(
                confidence,
                (int, float),
            )
            else "-"
        )

        table.add_row(
            str(event_type),
            str(title),
            start_text,
            end_text,
            objects_text,
            confidence_text,
        )

    console.print(table)

    # Detailed descriptions
    for index, event in enumerate(
        reconstructed,
        start=1,
    ):

        title = getattr(
            event,
            "title",
            None,
        ) or getattr(
            event,
            "event_type",
            "Forensic activity",
        )

        description = getattr(
            event,
            "description",
            None,
        )

        if description:

            console.print()

            console.print(
                Panel(
                    str(description),
                    title=f"Activity #{index}: {title}",
                    border_style="brand.dim",
                )
            )


def _print_forensic_summary(console, result) -> None:
    """
    Display the final AI forensic summary.
    """

    summary = getattr(
        result,
        "forensic_summary",
        None,
    )

    section_header(
        console,
        "Final Forensic Summary",
    )

    if summary is None:

        warn(
            console,
            "No forensic summary was generated.",
        )

        return

    headline = getattr(
        summary,
        "headline",
        None,
    )

    summary_text = getattr(
        summary,
        "summary",
        None,
    )

    start_time = getattr(
        summary,
        "start_time",
        None,
    )

    end_time = getattr(
        summary,
        "end_time",
        None,
    )

    event_count = getattr(
        summary,
        "event_count",
        None,
    )

    objects_detected = getattr(
        summary,
        "objects_detected",
        None,
    )

    metadata = getattr(
        summary,
        "metadata",
        None,
    )

    if not isinstance(
        metadata,
        dict,
    ):
        metadata = {}

    confidence_label = metadata.get(
        "confidence_label"
    )

    # ---------------------------------------------------------
    # Main summary
    # ---------------------------------------------------------

    if headline:

        console.print(
            Panel(
                str(headline),
                title="INCIDENT / ACTIVITY",
                border_style="brand",
                expand=False,
            )
        )

    if summary_text:

        console.print(
            Panel(
                str(summary_text),
                title="FORENSIC SUMMARY",
                border_style="brand.dim",
                expand=False,
            )
        )

    # ---------------------------------------------------------
    # Summary details
    # ---------------------------------------------------------

    details = Table(
        border_style="brand.dim",
        show_header=False,
    )

    details.add_column(
        "Field",
        style="brand",
    )

    details.add_column(
        "Value",
    )

    if start_time:

        details.add_row(
            "Start time",
            start_time.isoformat(
                sep=" ",
                timespec="seconds",
            ),
        )

    if end_time:

        details.add_row(
            "End time",
            end_time.isoformat(
                sep=" ",
                timespec="seconds",
            ),
        )

    if event_count is not None:

        details.add_row(
            "Events reconstructed",
            str(event_count),
        )

    if objects_detected:

        if isinstance(
            objects_detected,
            (list, tuple, set),
        ):

            objects_text = ", ".join(
                str(item)
                for item in objects_detected
            )

        else:

            objects_text = str(
                objects_detected
            )

        details.add_row(
            "Objects detected",
            objects_text,
        )

    if confidence_label:

        details.add_row(
            "Confidence",
            str(confidence_label),
        )

    if details.row_count > 0:

        console.print()
        console.print(details)

    # ---------------------------------------------------------
    # Key events
    # ---------------------------------------------------------

    key_events = getattr(
        summary,
        "key_events",
        None,
    )

    if key_events:

        console.print()

        key_table = Table(
            border_style="brand.dim",
            header_style="brand",
            title="Key Forensic Events",
        )

        key_table.add_column(
            "#",
            width=5,
        )

        key_table.add_column(
            "Event",
        )

        for index, item in enumerate(
            key_events,
            start=1,
        ):

            key_table.add_row(
                str(index),
                str(item),
            )

        console.print(key_table)


def analyze(
    video_path: Path = typer.Argument(
        ...,
        help="Path to the video file to analyze",
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        help=(
            "[reserved] Where to write analysis artifacts; "
            "currently events are only printed"
        ),
    ),
    sample_fps: float = typer.Option(
        2.0,
        "--sample-fps",
        help="Frames per second to sample for analysis",
    ),
    model: str = typer.Option(
        DEFAULT_MODEL,
        "--model",
        help="Path to the YOLO model weights",
    ),
    start_time: Optional[datetime] = typer.Option(
        None,
        "--start-time",
        help=(
            "Recording start time (ISO 8601), used to convert "
            "frame offsets to absolute timestamps. "
            "Defaults to now if omitted."
        ),
    ),
) -> None:
    """
    Run the complete video forensic analysis pipeline.

    Pipeline:

    motion
    -> YOLO
    -> tracking
    -> forensic events
    -> AI event reconstruction
    -> final forensic summary
    """

    console = get_console()

    section_header(
        console,
        "Analyze",
    )

    resolved = require_file(
        video_path,
        console,
    )

    # ---------------------------------------------------------
    # Import analysis service
    # ---------------------------------------------------------

    try:

        from backend.video.analysis.service import (
            VideoAnalysisService,
        )

    except ImportError as exc:

        error(
            console,
            (
                "Video analysis requires optional AI "
                f"dependencies that aren't installed: {exc}"
            ),
        )

        console.print(
            "[dim]Install them with: "
            "pip install ultralytics av[/dim]"
        )

        raise typer.Exit(
            code=ExitCode.MISSING_DEPENDENCY
        )

    # ---------------------------------------------------------
    # Start timestamp
    # ---------------------------------------------------------

    video_start = (
        start_time
        or datetime.now(timezone.utc)
    )

    console.print(
        f"[field]Video:[/field] "
        f"[path]{resolved}[/path]"
    )

    console.print(
        f"[field]Model:[/field] {model}"
    )

    console.print(
        f"[field]Sample FPS:[/field] "
        f"{sample_fps}"
    )

    console.print(
        f"[field]Start time:[/field] "
        f"{video_start.isoformat()}\n"
    )

    # ---------------------------------------------------------
    # Initialize AI service
    # ---------------------------------------------------------

    try:

        service = VideoAnalysisService(
            yolo_model=model
        )

    except Exception as exc:

        error(
            console,
            f"Could not initialize the AI pipeline: {exc}",
        )

        raise typer.Exit(
            code=ExitCode.MISSING_DEPENDENCY
        )

    # ---------------------------------------------------------
    # Run complete analysis
    # ---------------------------------------------------------

    with console.status(
        (
            "[brand]"
            "Running AI pipeline "
            "(probe → frames → motion → YOLO → "
            "events → reconstruction → summary)..."
            "[/brand]"
        ),
        spinner="arc",
    ):

        try:

            result = service.analyze(
                video_id=resolved.stem,
                camera_id="CH-CLI",
                video_path=resolved,
                video_start_time=video_start,
                frame_sample_fps=sample_fps,
            )

        except FileNotFoundError as exc:

            error(
                console,
                str(exc),
            )

            raise typer.Exit(
                code=ExitCode.FILE_NOT_FOUND
            )

        except Exception as exc:

            error(
                console,
                f"Video analysis failed: {exc}",
            )

            raise typer.Exit(
                code=ExitCode.GENERAL_ERROR
            )

    # =========================================================
    # VIDEO METADATA
    # =========================================================

    console.print(
        f"[field]Frames analyzed:[/field] "
        f"{result.frame_count_analyzed}   "
        f"[field]Duration:[/field] "
        f"{result.metadata.duration_seconds or 0:.1f}s   "
        f"[field]Resolution:[/field] "
        f"{result.metadata.width}x"
        f"{result.metadata.height}\n"
    )

    # =========================================================
    # RAW FORENSIC EVENTS
    # =========================================================

    section_header(
        console,
        "Forensic Events",
    )

    if not result.events:

        warn(
            console,
            "No events were detected.",
        )

    else:

        table = Table(
            border_style="brand.dim",
            header_style="brand",
            title=f"{len(result.events)} event(s)",
        )

        table.add_column(
            "Type"
        )

        table.add_column(
            "Object"
        )

        table.add_column(
            "Start"
        )

        table.add_column(
            "End"
        )

        table.add_column(
            "Confidence"
        )

        table.add_column(
            "Track ID"
        )

        for event in result.events:

            table.add_row(
                event.event_type,

                event.object_type
                or "[dim]-[/dim]",

                event.start_time.isoformat(
                    sep=" ",
                    timespec="seconds",
                ),

                event.end_time.isoformat(
                    sep=" ",
                    timespec="seconds",
                ),

                (
                    f"{event.confidence:.2f}"
                    if event.confidence is not None
                    else "[dim]-[/dim]"
                ),

                (
                    str(event.track_id)
                    if event.track_id is not None
                    else "[dim]-[/dim]"
                ),
            )

        console.print(table)

    # =========================================================
    # AI FORENSIC EVENT RECONSTRUCTION
    # =========================================================

    _print_reconstructed_events(
        console,
        result,
    )

    # =========================================================
    # FINAL FORENSIC SUMMARY
    # =========================================================

    _print_forensic_summary(
        console,
        result,
    )

    # =========================================================
    # COMPLETE
    # =========================================================

    success(
        console,
        (
            "Analysis complete — "
            f"{len(result.events)} event(s) found, "
            f"{len(getattr(result, 'reconstructed_events', []))} "
            "higher-level activity(s) reconstructed."
        ),
    )

    if output:

        warn(
            console,
            (
                "--output is reserved for a future "
                "artifact-writing mode; results were "
                "printed above only."
            ),
        )