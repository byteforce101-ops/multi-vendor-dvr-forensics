"""backend/cli/interactive.py — TRACEX guided pipeline mode.

Triggered when `dvrforensics` is run with no subcommand: shows a big
TRACEX banner, prompts for a file path, then walks the file through
detect -> parse -> extract -> AI analyze automatically, printing each
step's output as it goes, ending with an aggregated AI analysis summary
and an optional natural-language Q&A over the detected events. Loops back
to prompt for another file when finished. Nothing here duplicates
backend/core, backend/parsers, backend/video logic — it only orchestrates
the same functions the detect/parse/extract/analyze commands already call,
plus reuses the existing Groq client wiring from
backend/core/search/query_parser.py for the Q&A step.
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
    body = Text(_big_text("TRACEX"), style="bold bright_cyan")
    body.append("\n")
    body.append("T R A C E   ·   R E C O V E R   ·   A N A L Y Z E", style="bold magenta")
    console.print(Panel(body, border_style="bright_cyan", expand=False, padding=(1, 3)))


def _ask_about_video(console, events: list, video_path: Path) -> None:
    """Conversational Q&A over the events detected in this run, via Groq.

    Reuses the same Groq() client wiring already configured in
    backend/core/search/query_parser.py (GROQ_API_KEY from env) — this is
    intentionally a free-form chat over the in-memory event list from this
    one run, not the structured case-wide filter search that `dvrforensics
    search` does against persisted DB events.
    """
    if not events:
        return

    try:
        from groq import Groq
    except ImportError:
        warn(console, "Q&A requires the 'groq' package, which isn't installed — skipping.")
        return

    try:
        client = Groq()
    except Exception as exc:
        warn(console, f"Q&A unavailable (Groq client could not initialize: {exc}) — skipping.")
        return

    event_lines = "\n".join(
        f"- {e.event_type} ({e.object_type or 'n/a'}) on {cam} at "
        f"{e.start_time.isoformat(sep=' ', timespec='seconds')}, confidence {e.confidence:.2f}"
        + (f" — {e.metadata['note']}" if e.metadata.get("note") else "")
        for cam, e in sorted(events, key=lambda pair: pair[1].start_time)
    )

    system_prompt = (
        "You are a forensic video-analysis assistant. You are given a timeline of "
        "AI-detected events from one video file, in chronological order. Events "
        "starting with REVIEW_FLAG_ are heuristic candidates for human review "
        "(bounding-box overlap or sudden deceleration) — they are NOT confirmed "
        "incidents. Never state that an accident/collision/incident definitely "
        "happened; at most say the data flags a moment worth a human reviewing. "
        "Answer using ONLY this event data, concisely. If the data doesn't support "
        "an answer, say so plainly rather than guessing.\n\n"
        f"Video: {video_path.name}\n\nDetected events:\n{event_lines}"
    )

    section_header(console, "Ask About This Video")
    console.print("[dim]Type a question, or press Enter with nothing typed to finish.[/dim]\n")

    history = [{"role": "system", "content": system_prompt}]

    while True:
        question = Prompt.ask("[bold bright_cyan]Query[/bold bright_cyan]", default="", show_default=False)
        if not question.strip():
            break

        history.append({"role": "user", "content": question})
        with console.status("[brand]Thinking...[/brand]", spinner="dots"):
            try:
                import os

                resp = client.chat.completions.create(
                    model=os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"),
                    max_tokens=400,
                    messages=history,
                )
                answer = resp.choices[0].message.content.strip()
            except Exception as exc:
                error(console, f"Query failed: {exc}")
                continue

        history.append({"role": "assistant", "content": answer})
        console.print(Panel(answer, border_style="bright_cyan", title="Answer"))


def _run_pipeline_once(console) -> None:
    path_str = Prompt.ask("[bold bright_cyan]Evidence / video file path[/bold bright_cyan]")
    path = Path(path_str.strip('"').strip("'")).expanduser().resolve()

    if not path.is_file():
        error(console, f"File not found: {path}")
        return

    from backend.parsers.registry import ParserManager

    manager = ParserManager()

    # ---- Step 1: Detect ----
    section_header(console, "Step 1 / 4 — Detect")
    with console.status("[brand]Scanning file signature...[/brand]", spinner="bouncingBar"):
        parser, confidence, info = manager.detect(str(path))

    if parser is None:
        error(console, "No registered parser recognized this file.")
        return

    t = fact_table()
    t.add_row("[field]File:[/field]", f"[path]{path}[/path]")
    t.add_row("[field]Size:[/field]", human_size(path.stat().st_size))
    t.add_row("[field]Vendor:[/field]", f"[ok]{parser.vendor_name}[/ok]  ({confidence * 100:.0f}%)")
    console.print(t)

    # ---- Step 2: Parse ----
    section_header(console, "Step 2 / 4 — Parse")
    out_dir = Path("./tracex_output") / path.stem
    with console.status("[brand]Parsing evidence...[/brand]", spinner="arc"):
        parse_result = manager.parse(str(path), str(out_dir))

    for w in parse_result.warnings:
        warn(console, w)
    if not parse_result.success:
        for e in parse_result.errors:
            error(console, e)
        return

    ptable = Table(border_style="brand.dim", header_style="brand", title=f"{len(parse_result.recordings)} recording(s)")
    for col in ("Recording ID", "Camera", "Timestamp", "Status"):
        ptable.add_column(col)
    for rec in parse_result.recordings:
        ptable.add_row(
            rec.recording_id,
            rec.camera_id,
            rec.original_timestamp.isoformat(sep=" ", timespec="seconds") if rec.original_timestamp else "unknown",
            rec.recovery_status,
        )
    console.print(ptable)

    # ---- Step 3: Extract ----
    section_header(console, "Step 3 / 4 — Extract")

    already_usable = [
        rec for rec in parse_result.recordings
        if rec.extracted_path and Path(rec.extracted_path).is_file()
    ]

    if len(already_usable) == len(parse_result.recordings):
        console.print("[dim]Recordings are already directly playable for this vendor — nothing to carve out, skipping ffmpeg extraction.[/dim]")
        recovered = already_usable
        etable = Table(border_style="brand.dim", header_style="brand", title="Recordings Ready For Analysis")
        for col in ("Recording ID", "Camera", "Status", "File"):
            etable.add_column(col)
        for rec in recovered:
            etable.add_row(rec.recording_id, rec.camera_id, rec.recovery_status, rec.extracted_path)
        console.print(etable)
    else:
        if shutil.which("ffmpeg") is None:
            warn(console, "ffmpeg not found on PATH — skipping extraction and AI analysis.")
            return

        with console.status("[brand]Extracting recordings...[/brand]", spinner="dots"):
            extract_result = manager.extract(str(path), str(out_dir), parse_result)

        for w in extract_result.warnings:
            warn(console, w)
        if not extract_result.success:
            for e in extract_result.errors:
                error(console, e)

        etable = Table(border_style="brand.dim", header_style="brand", title="Extraction Results")
        for col in ("Recording ID", "Status", "File"):
            etable.add_column(col)
        recovered = []
        for rec in extract_result.recordings:
            etable.add_row(rec.recording_id, rec.recovery_status, rec.extracted_path or "-")
            if rec.extracted_path:
                recovered.append(rec)
        console.print(etable)

    if not recovered:
        warn(console, "No recordings were recoverable — nothing to analyze.")
        return

    # ---- Step 4: AI Analysis ----
    section_header(console, "Step 4 / 4 — AI Analysis")
    try:
        from backend.video.analysis.service import VideoAnalysisService
    except ImportError:
        warn(console, "AI analysis dependencies (ultralytics/av) not installed — skipping.")
        return

    service = VideoAnalysisService(yolo_model="yolo26n.pt")
    all_events = []  # list of (camera_id, event)
    for rec in recovered:
        with console.status(f"[brand]Analyzing {rec.recording_id}...[/brand]", spinner="arc"):
            try:
                result = service.analyze(
                    video_id=rec.recording_id,
                    camera_id=rec.camera_id,
                    video_path=Path(rec.extracted_path),
                    video_start_time=rec.original_timestamp or datetime.now(timezone.utc),
                    frame_sample_fps=2.0,
                )
                all_events.extend((rec.camera_id, e) for e in result.events)
                success(console, f"{rec.recording_id}: {len(result.events)} event(s)")
            except Exception as exc:
                error(console, f"{rec.recording_id}: analysis failed ({exc})")

    if not all_events:
        warn(console, "No events detected across any recording.")
        return

    section_header(console, "Final AI Analysis Summary")
    summary = Table(border_style="bright_cyan", header_style="bold bright_cyan", title=f"{len(all_events)} total event(s)")
    for col in ("Type", "Object", "Camera", "Start", "Confidence"):
        summary.add_column(col)
    for cam, e in sorted(all_events, key=lambda pair: pair[1].start_time):
        summary.add_row(
            e.event_type,
            e.object_type or "-",
            cam,
            e.start_time.isoformat(sep=" ", timespec="seconds"),
            f"{e.confidence:.2f}" if e.confidence is not None else "-",
        )
    console.print(summary)
    success(console, f"TRACEX pipeline complete — {len(all_events)} event(s) across {len(recovered)} recording(s).")

    _ask_about_video(console, all_events, path)


def run() -> None:
    console = get_console()
    print_tracex_banner(console)

    while True:
        _run_pipeline_once(console)
        console.print()
        if not Confirm.ask("[bold bright_cyan]Analyze another file?[/bold bright_cyan]", default=False):
            break
        console.print()