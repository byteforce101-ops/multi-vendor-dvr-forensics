"""backend/cli/interactive.py — TRACEX guided pipeline mode.

Triggered when `dvrforensics` is run with no subcommand: shows a big
TRACEX banner, prompts for a file path, then walks the file through
detect -> parse -> extract -> AI analyze automatically, printing each
step's output as it goes.

The AI analysis stage also includes:
    - object detection
    - motion detection
    - forensic event generation
    - AI forensic event reconstruction
    - final forensic summary

The existing natural-language Q&A remains available at the end.

Nothing here duplicates backend/core, backend/parsers, backend/video logic —
this file only orchestrates the existing services.
"""

from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path

from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.text import Text

from backend.cli.theme import (
    error,
    fact_table,
    get_console,
    human_size,
    section_header,
    success,
    warn,
)


_TRACEX_FONT = {
    "T": ["██████", "··██··", "··██··", "··██··", "··██··", "··██··"],
    "R": ["█████·", "██··██", "█████·", "██·██·", "██··██", "██··██"],
    "A": ["·████·", "██··██", "██████", "██··██", "██··██", "██··██"],
    "C": ["·█████", "██····", "██····", "██····", "██····", "·█████"],
    "E": ["██████", "██····", "█████·", "██····", "██····", "██████"],
    "X": ["██··██", "·████·", "··██··", "··██··", "·████·", "██··██"],
}


def _big_text(word: str) -> str:
    rows = ["" for _ in range(6)]

    for ch in word:
        glyph = _TRACEX_FONT.get(ch.upper())

        if glyph is None:
            continue

        for i in range(6):
            rows[i] += glyph[i] + " "

    return "\n".join(rows).replace("·", " ")


def print_tracex_banner(console) -> None:
    body = Text(
        _big_text("TRACEX"),
        style="bold bright_cyan",
    )

    body.append("\n")

    body.append(
        "T R A C E   ·   R E C O V E R   ·   A N A L Y Z E",
        style="bold magenta",
    )

    console.print(
        Panel(
            body,
            border_style="bright_cyan",
            expand=False,
            padding=(1, 3),
        )
    )


# =========================================================
# EXISTING Q&A
# =========================================================

def _ask_about_video(
    console,
    events: list,
    video_path: Path,
) -> None:
    """Conversational Q&A over the events detected in this run."""

    if not events:
        return

    try:
        from groq import Groq

    except ImportError:

        warn(
            console,
            "Q&A requires the 'groq' package, which isn't installed — skipping.",
        )

        return

    try:
        client = Groq()

    except Exception as exc:

        warn(
            console,
            (
                "Q&A unavailable "
                f"(Groq client could not initialize: {exc}) — skipping."
            ),
        )

        return

    event_lines = "\n".join(
        f"- {e.event_type} ({e.object_type or 'n/a'}) "
        f"on {cam} at "
        f"{e.start_time.isoformat(sep=' ', timespec='seconds')}, "
        f"confidence {e.confidence:.2f}"
        + (
            f" — {e.metadata['note']}"
            if e.metadata.get("note")
            else ""
        )
        for cam, e in sorted(
            events,
            key=lambda pair: pair[1].start_time,
        )
    )

    system_prompt = (
        "You are a forensic video-analysis assistant. "
        "You are given a timeline of AI-detected events from one video file, "
        "in chronological order. Events starting with REVIEW_FLAG_ are "
        "heuristic candidates for human review (bounding-box overlap or "
        "sudden deceleration) — they are NOT confirmed incidents. "
        "Never state that an accident/collision/incident definitely happened; "
        "at most say the data flags a moment worth a human reviewing. "
        "Answer using ONLY this event data, concisely. "
        "If the data doesn't support an answer, say so plainly rather than guessing.\n\n"
        f"Video: {video_path.name}\n\n"
        f"Detected events:\n{event_lines}"
    )

    section_header(
        console,
        "Ask About This Video",
    )

    console.print(
        "[dim]Type a question, or press Enter with nothing typed to finish.[/dim]\n"
    )

    history = [
        {
            "role": "system",
            "content": system_prompt,
        }
    ]

    while True:

        question = Prompt.ask(
            "[bold bright_cyan]Query[/bold bright_cyan]",
            default="",
            show_default=False,
        )

        if not question.strip():
            break

        history.append(
            {
                "role": "user",
                "content": question,
            }
        )

        with console.status(
            "[brand]Thinking...[/brand]",
            spinner="dots",
        ):

            try:

                import os

                resp = client.chat.completions.create(
                    model=os.getenv(
                        "GROQ_MODEL",
                        "openai/gpt-oss-120b",
                    ),
                    max_tokens=400,
                    messages=history,
                )

                answer = (
                    resp.choices[0]
                    .message.content
                    .strip()
                )

            except Exception as exc:

                error(
                    console,
                    f"Query failed: {exc}",
                )

                continue

        history.append(
            {
                "role": "assistant",
                "content": answer,
            }
        )

        console.print(
            Panel(
                answer,
                border_style="bright_cyan",
                title="Answer",
            )
        )


# =========================================================
# AI FORENSIC EVENT RECONSTRUCTION
# =========================================================

def _print_reconstructed_events(
    console,
    reconstructed_events: list,
) -> None:
    """Display higher-level reconstructed forensic activities."""

    section_header(
        console,
        "AI Forensic Event Reconstruction",
    )

    if not reconstructed_events:

        warn(
            console,
            "No higher-level forensic activities were reconstructed.",
        )

        return

    table = Table(
        border_style="bright_cyan",
        header_style="bold bright_cyan",
        title=(
            f"{len(reconstructed_events)} "
            "reconstructed activity(s)"
        ),
    )

    table.add_column("Type")
    table.add_column("Activity")
    table.add_column("Start")
    table.add_column("End")
    table.add_column("Objects")
    table.add_column("Confidence")

    for event in reconstructed_events:

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

        if isinstance(
            objects,
            (list, tuple, set),
        ):

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

        start_text = (
            start_time.isoformat(
                sep=" ",
                timespec="seconds",
            )
            if start_time
            else "-"
        )

        end_text = (
            end_time.isoformat(
                sep=" ",
                timespec="seconds",
            )
            if end_time
            else "-"
        )

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

    # ---------------------------------------------------------
    # Detailed reconstruction descriptions
    # ---------------------------------------------------------

    for index, event in enumerate(
        reconstructed_events,
        start=1,
    ):

        description = getattr(
            event,
            "description",
            None,
        )

        title = getattr(
            event,
            "title",
            None,
        ) or getattr(
            event,
            "event_type",
            "Forensic activity",
        )

        if description:

            console.print()

            console.print(
                Panel(
                    str(description),
                    title=(
                        f"Activity #{index}: "
                        f"{title}"
                    ),
                    border_style="bright_cyan",
                    expand=False,
                )
            )


# =========================================================
# FINAL FORENSIC SUMMARY
# =========================================================

def _print_forensic_summary(
    console,
    summaries: list,
) -> None:
    """Display the final forensic summary for the analysis."""

    section_header(
        console,
        "Final AI Forensic Summary",
    )

    if not summaries:

        warn(
            console,
            "No forensic summary was generated.",
        )

        return

    # ---------------------------------------------------------
    # If there is one summary, display it directly.
    # ---------------------------------------------------------

    if len(summaries) == 1:

        summary = summaries[0]

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

        if headline:

            console.print(
                Panel(
                    str(headline),
                    title="INCIDENT / ACTIVITY",
                    border_style="bright_cyan",
                    expand=False,
                )
            )

        if summary_text:

            console.print(
                Panel(
                    str(summary_text),
                    title="FORENSIC SUMMARY",
                    border_style="bright_cyan",
                    expand=False,
                )
            )

        details = Table(
            border_style="brand.dim",
            show_header=False,
        )

        details.add_column(
            "Field",
            style="bold bright_cyan",
        )

        details.add_column(
            "Value",
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
            {},
        )

        if not isinstance(
            metadata,
            dict,
        ):
            metadata = {}

        confidence_label = metadata.get(
            "confidence_label"
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

        if details.row_count:

            console.print()
            console.print(details)

        # -----------------------------------------------------
        # Key events
        # -----------------------------------------------------

        key_events = getattr(
            summary,
            "key_events",
            None,
        )

        if key_events:

            console.print()

            key_table = Table(
                border_style="bright_cyan",
                header_style="bold bright_cyan",
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

        return

    # ---------------------------------------------------------
    # Multiple recordings
    # ---------------------------------------------------------

    console.print(
        Panel(
            (
                f"{len(summaries)} recording summaries "
                "were generated."
            ),
            title="FORENSIC ANALYSIS",
            border_style="bright_cyan",
            expand=False,
        )
    )

    for index, summary in enumerate(
        summaries,
        start=1,
    ):

        headline = getattr(
            summary,
            "headline",
            "Activity detected",
        )

        summary_text = getattr(
            summary,
            "summary",
            None,
        )

        console.print()

        console.print(
            Panel(
                str(
                    summary_text
                    or headline
                ),
                title=(
                    f"Recording #{index} — "
                    f"{headline}"
                ),
                border_style="bright_cyan",
                expand=False,
            )
        )


# =========================================================
# MAIN PIPELINE
# =========================================================

def _run_pipeline_once(console) -> None:

    path_str = Prompt.ask(
        "[bold bright_cyan]"
        "Evidence / video file path"
        "[/bold bright_cyan]"
    )

    path = (
        Path(
            path_str.strip('"').strip("'")
        )
        .expanduser()
        .resolve()
    )

    if not path.is_file():

        error(
            console,
            f"File not found: {path}",
        )

        return

    from backend.parsers.registry import (
        ParserManager,
    )

    manager = ParserManager()

    # =========================================================
    # STEP 1 — DETECT
    # =========================================================

    section_header(
        console,
        "Step 1 / 4 — Detect",
    )

    with console.status(
        "[brand]Scanning file signature...[/brand]",
        spinner="bouncingBar",
    ):

        parser, confidence, info = (
            manager.detect(
                str(path)
            )
        )

    if parser is None:

        error(
            console,
            "No registered parser recognized this file.",
        )

        return

    t = fact_table()

    t.add_row(
        "[field]File:[/field]",
        f"[path]{path}[/path]",
    )

    t.add_row(
        "[field]Size:[/field]",
        human_size(
            path.stat().st_size
        ),
    )

    t.add_row(
        "[field]Vendor:[/field]",
        (
            f"[ok]{parser.vendor_name}[/ok]  "
            f"({confidence * 100:.0f}%)"
        ),
    )

    console.print(t)

    # =========================================================
    # STEP 2 — PARSE
    # =========================================================

    section_header(
        console,
        "Step 2 / 4 — Parse",
    )

    out_dir = (
        Path("./tracex_output")
        / path.stem
    )

    with console.status(
        "[brand]Parsing evidence...[/brand]",
        spinner="arc",
    ):

        parse_result = manager.parse(
            str(path),
            str(out_dir),
        )

    for warning_message in (
        parse_result.warnings
    ):

        warn(
            console,
            warning_message,
        )

    if not parse_result.success:

        for parse_error in (
            parse_result.errors
        ):

            error(
                console,
                parse_error,
            )

        return

    ptable = Table(
        border_style="brand.dim",
        header_style="brand",
        title=(
            f"{len(parse_result.recordings)} "
            "recording(s)"
        ),
    )

    for column in (
        "Recording ID",
        "Camera",
        "Timestamp",
        "Status",
    ):

        ptable.add_column(column)

    for rec in parse_result.recordings:

        ptable.add_row(
            rec.recording_id,
            rec.camera_id,
            (
                rec.original_timestamp.isoformat(
                    sep=" ",
                    timespec="seconds",
                )
                if rec.original_timestamp
                else "unknown"
            ),
            rec.recovery_status,
        )

    console.print(ptable)

    # =========================================================
    # STEP 3 — EXTRACT
    # =========================================================

    section_header(
        console,
        "Step 3 / 4 — Extract",
    )

    already_usable = [
        rec
        for rec in parse_result.recordings
        if rec.extracted_path
        and Path(
            rec.extracted_path
        ).is_file()
    ]

    if len(already_usable) == len(
        parse_result.recordings
    ):

        console.print(
            "[dim]"
            "Recordings are already directly playable "
            "for this vendor — nothing to carve out, "
            "skipping ffmpeg extraction."
            "[/dim]"
        )

        recovered = already_usable

        etable = Table(
            border_style="brand.dim",
            header_style="brand",
            title="Recordings Ready For Analysis",
        )

        for column in (
            "Recording ID",
            "Camera",
            "Status",
            "File",
        ):

            etable.add_column(column)

        for rec in recovered:

            etable.add_row(
                rec.recording_id,
                rec.camera_id,
                rec.recovery_status,
                rec.extracted_path,
            )

        console.print(etable)

    else:

        if shutil.which("ffmpeg") is None:

            warn(
                console,
                (
                    "ffmpeg not found on PATH — "
                    "skipping extraction and AI analysis."
                ),
            )

            return

        with console.status(
            "[brand]Extracting recordings...[/brand]",
            spinner="dots",
        ):

            extract_result = manager.extract(
                str(path),
                str(out_dir),
                parse_result,
            )

        for warning_message in (
            extract_result.warnings
        ):

            warn(
                console,
                warning_message,
            )

        if not extract_result.success:

            for extraction_error in (
                extract_result.errors
            ):

                error(
                    console,
                    extraction_error,
                )

        etable = Table(
            border_style="brand.dim",
            header_style="brand",
            title="Extraction Results",
        )

        for column in (
            "Recording ID",
            "Status",
            "File",
        ):

            etable.add_column(column)

        recovered = []

        for rec in extract_result.recordings:

            etable.add_row(
                rec.recording_id,
                rec.recovery_status,
                rec.extracted_path or "-",
            )

            if rec.extracted_path:

                recovered.append(rec)

        console.print(etable)

    if not recovered:

        warn(
            console,
            (
                "No recordings were recoverable — "
                "nothing to analyze."
            ),
        )

        return

    # =========================================================
    # STEP 4 — AI ANALYSIS
    # =========================================================

    section_header(
        console,
        "Step 4 / 4 — AI Analysis",
    )

    try:

        from backend.video.analysis.service import (
            VideoAnalysisService,
        )

    except ImportError:

        warn(
            console,
            (
                "AI analysis dependencies "
                "(ultralytics/av) not installed — "
                "skipping."
            ),
        )

        return

    service = VideoAnalysisService(
        yolo_model="yolo26n.pt"
    )

    # Existing Q&A expects this structure:
    # [(camera_id, event), ...]
    all_events = []

    # New reconstruction results
    all_reconstructed_events = []

    # New final summaries
    all_summaries = []

    # =========================================================
    # ANALYZE EACH RECORDING
    # =========================================================

    for rec in recovered:

        with console.status(
            (
                f"[brand]Analyzing "
                f"{rec.recording_id}...[/brand]"
            ),
            spinner="arc",
        ):

            try:

                result = service.analyze(
                    video_id=rec.recording_id,
                    camera_id=rec.camera_id,
                    video_path=Path(
                        rec.extracted_path
                    ),
                    video_start_time=(
                        rec.original_timestamp
                        or datetime.now(timezone.utc)
                    ),
                    frame_sample_fps=2.0,
                )

                # ---------------------------------------------
                # Existing events
                # ---------------------------------------------

                all_events.extend(
                    (
                        rec.camera_id,
                        event,
                    )
                    for event in result.events
                )

                # ---------------------------------------------
                # AI reconstruction
                # ---------------------------------------------

                reconstructed = getattr(
                    result,
                    "reconstructed_events",
                    [],
                )

                if reconstructed:

                    all_reconstructed_events.extend(
                        reconstructed
                    )

                # ---------------------------------------------
                # Final forensic summary
                # ---------------------------------------------

                forensic_summary = getattr(
                    result,
                    "forensic_summary",
                    None,
                )

                if forensic_summary is not None:

                    all_summaries.append(
                        forensic_summary
                    )

                success(
                    console,
                    (
                        f"{rec.recording_id}: "
                        f"{len(result.events)} event(s)"
                    ),
                )

            except Exception as exc:

                error(
                    console,
                    (
                        f"{rec.recording_id}: "
                        f"analysis failed ({exc})"
                    ),
                )

    # =========================================================
    # NO EVENTS
    # =========================================================

    if not all_events:

        warn(
            console,
            "No events detected across any recording.",
        )

        # Even if no raw events were detected,
        # display a summary if the backend produced one.

        if all_summaries:

            _print_forensic_summary(
                console,
                all_summaries,
            )

        return

    # =========================================================
    # EXISTING FINAL EVENT TABLE
    # =========================================================

    section_header(
        console,
        "Final AI Analysis Summary",
    )

    summary_table = Table(
        border_style="bright_cyan",
        header_style="bold bright_cyan",
        title=(
            f"{len(all_events)} "
            "total event(s)"
        ),
    )

    for column in (
        "Type",
        "Object",
        "Camera",
        "Start",
        "Confidence",
    ):

        summary_table.add_column(
            column
        )

    for cam, event in sorted(
        all_events,
        key=lambda pair: pair[1].start_time,
    ):

        summary_table.add_row(
            event.event_type,
            event.object_type or "-",
            cam,
            event.start_time.isoformat(
                sep=" ",
                timespec="seconds",
            ),
            (
                f"{event.confidence:.2f}"
                if event.confidence is not None
                else "-"
            ),
        )

    console.print(
        summary_table
    )

    # =========================================================
    # AI FORENSIC EVENT RECONSTRUCTION
    # =========================================================

    _print_reconstructed_events(
        console,
        all_reconstructed_events,
    )

    # =========================================================
    # FINAL FORENSIC SUMMARY
    # =========================================================

    _print_forensic_summary(
        console,
        all_summaries,
    )

    # =========================================================
    # COMPLETE
    # =========================================================

    success(
        console,
        (
            "TRACEX pipeline complete — "
            f"{len(all_events)} event(s) across "
            f"{len(recovered)} recording(s). "
            f"{len(all_reconstructed_events)} "
            "higher-level forensic activity(s) reconstructed."
        ),
    )

    # =========================================================
    # EXISTING Q&A
    # =========================================================

    _ask_about_video(
        console,
        all_events,
        path,
    )


# =========================================================
# INTERACTIVE ENTRY POINT
# =========================================================

def run() -> None:

    console = get_console()

    print_tracex_banner(
        console
    )

    while True:

        _run_pipeline_once(
            console
        )

        console.print()

        if not Confirm.ask(
            (
                "[bold bright_cyan]"
                "Analyze another file?"
                "[/bold bright_cyan]"
            ),
            default=False,
        ):

            break

        console.print()