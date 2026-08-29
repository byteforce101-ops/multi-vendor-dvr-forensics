"""dvrforensics extract PATH"""

from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

import typer
from rich.table import Table

from backend.cli.common import require_file
from backend.cli.exit_codes import ExitCode
from backend.cli.theme import error, get_console, section_header, success, warn

DEFAULT_OUTPUT = "./recovered"


def extract(
    path: Path = typer.Argument(..., help="Path to the evidence file"),
    output: Path = typer.Option(DEFAULT_OUTPUT, "--output", help="Output directory for extracted recordings"),
    camera: Optional[str] = typer.Option(
        None, "--camera", help="[not yet supported by the parser layer] Filter to a single camera ID"
    ),
    recording: Optional[str] = typer.Option(
        None, "--recording", help="[not yet supported by the parser layer] Filter to a single recording ID"
    ),
    from_time: Optional[datetime] = typer.Option(
        None, "--from", help="[not yet supported by the parser layer] Only recordings starting at/after this time"
    ),
    to_time: Optional[datetime] = typer.Option(
        None, "--to", help="[not yet supported by the parser layer] Only recordings starting at/before this time"
    ),
) -> None:
    """Parse an evidence file, then extract every recoverable recording.

    --camera/--recording/--from/--to are accepted now so scripts can be
    written against a stable interface, but BaseDVRParser.extract_recordings
    currently always operates on the full recording list returned by
    parse() — there's no per-recording filtering hook in the parser layer
    yet. Passing them prints a notice and extracts everything; wiring real
    filtering through ParserManager.extract() is a parser-layer change, not
    a CLI one.
    """
    from backend.parsers.registry import ParserManager

    console = get_console()
    section_header(console, "Extract")

    resolved = require_file(path, console)
    output_dir = output.expanduser().resolve()

    if shutil.which("ffmpeg") is None:
        error(console, "ffmpeg was not found on PATH. Extraction requires ffmpeg to mux recovered video.")
        raise typer.Exit(code=ExitCode.MISSING_DEPENDENCY)

    if any([camera, recording, from_time, to_time]):
        warn(
            console,
            "Recording filters (--camera/--recording/--from/--to) are accepted for forward "
            "compatibility but not yet applied — the parser layer doesn't support filtered "
            "extraction. All recoverable recordings will be extracted.",
        )

    manager = ParserManager()

    with console.status("[brand]Parsing evidence...[/brand]", spinner="arc"):
        parse_result = manager.parse(str(resolved), str(output_dir))

    for w in parse_result.warnings:
        warn(console, w)

    if not parse_result.success:
        for e in parse_result.errors:
            error(console, e)
        raise typer.Exit(code=ExitCode.CORRUPTED_EVIDENCE)

    if not parse_result.recordings:
        warn(console, "No recordings found to extract.")
        return

    with console.status(
        f"[brand]Extracting {len(parse_result.recordings)} recording(s) via ffmpeg...[/brand]",
        spinner="dots",
    ):
        extract_result = manager.extract(str(resolved), str(output_dir), parse_result)

    for w in extract_result.warnings:
        warn(console, w)
    for e in extract_result.errors:
        error(console, e)

    table = Table(border_style="brand.dim", header_style="brand", title="Extraction Results")
    table.add_column("Recording ID")
    table.add_column("Camera ID")
    table.add_column("Recovery Status")
    table.add_column("Extracted Path")

    recovered = 0
    for rec in extract_result.recordings:
        style = {"ORIGINAL": "ok", "RECOVERED": "ok", "PARTIAL": "warn"}.get(rec.recovery_status, "dim")
        if rec.recovery_status in ("ORIGINAL", "RECOVERED"):
            recovered += 1
        table.add_row(
            rec.recording_id,
            rec.camera_id,
            f"[{style}]{rec.recovery_status}[/{style}]",
            f"[path]{rec.extracted_path}[/path]" if rec.extracted_path else "[dim]-[/dim]",
        )

    console.print(table)

    if not extract_result.success:
        error(console, f"Extraction completed with errors ({recovered}/{len(extract_result.recordings)} recovered). Output: {output_dir}")
        raise typer.Exit(code=ExitCode.EXTRACTION_FAILED)

    if recovered == 0:
        warn(console, f"No recordings could be recovered (0/{len(extract_result.recordings)}) — see warnings above.")
    else:
        success(console, f"Extracted {recovered}/{len(extract_result.recordings)} recording(s) to {output_dir}")
