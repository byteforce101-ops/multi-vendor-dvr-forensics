"""dvrforensics parse PATH"""

from __future__ import annotations

from pathlib import Path

import typer
from rich.table import Table

from backend.cli.common import require_file
from backend.cli.exit_codes import ExitCode
from backend.cli.theme import error, get_console, section_header, success, warn

DEFAULT_OUTPUT = "./output"


def parse(
    path: Path = typer.Argument(..., help="Path to the evidence file"),
    output: Path = typer.Option(DEFAULT_OUTPUT, "--output", help="Output directory for parser artifacts"),
) -> None:
    """Detect → validate → parse an evidence file, then show discovered recordings."""
    from backend.parsers.common.base import ParseError
    from backend.parsers.registry import ParserManager

    console = get_console()
    section_header(console, "Parse")

    resolved = require_file(path, console)
    output_dir = output.expanduser().resolve()

    manager = ParserManager()

    with console.status("[brand]Detecting vendor...[/brand]", spinner="bouncingBar"):
        parser, confidence, _info = manager.detect(str(resolved))

    if parser is None:
        error(console, "No registered parser matched this evidence file.")
        raise typer.Exit(code=ExitCode.UNSUPPORTED_VENDOR)

    console.print(f"[field]Vendor:[/field] [ok]{parser.vendor_name}[/ok]  [dim]({confidence * 100:.0f}% confidence)[/dim]")

    with console.status("[brand]Validating evidence...[/brand]", spinner="dots"):
        is_valid, validate_warnings = parser.validate(str(resolved))

    for w in validate_warnings:
        warn(console, w)

    if not is_valid:
        error(console, "Evidence failed validation — see warnings above.")
        raise typer.Exit(code=ExitCode.CORRUPTED_EVIDENCE)

    with console.status("[brand]Parsing evidence...[/brand]", spinner="arc"):
        result = manager.parse(str(resolved), str(output_dir))

    for w in result.warnings:
        warn(console, w)

    if not result.success:
        for e in result.errors:
            error(console, e)
        code = ExitCode.CORRUPTED_EVIDENCE if result.error_code == ParseError.CORRUPTED_EVIDENCE else ExitCode.GENERAL_ERROR
        raise typer.Exit(code=code)

    if not result.recordings:
        warn(console, "Parsed successfully, but no recordings were found.")
        return

    table = Table(border_style="brand.dim", header_style="brand", title=f"{len(result.recordings)} recording(s) found")
    table.add_column("Recording ID")
    table.add_column("Camera ID")
    table.add_column("Timestamp")
    table.add_column("Duration")
    table.add_column("Resolution")
    table.add_column("Codec")
    table.add_column("Recovery Status")

    for rec in result.recordings:
        status = rec.recovery_status
        status_style = {"ORIGINAL": "ok", "RECOVERED": "ok", "PARTIAL": "warn"}.get(status, "dim")
        table.add_row(
            rec.recording_id,
            rec.camera_id,
            rec.original_timestamp.isoformat(sep=" ", timespec="seconds") if rec.original_timestamp else "[dim]unknown[/dim]",
            f"{rec.duration_seconds:.1f}s" if rec.duration_seconds is not None else "[dim]-[/dim]",
            rec.resolution or "[dim]-[/dim]",
            rec.codec or "[dim]-[/dim]",
            f"[{status_style}]{status}[/{status_style}]",
        )

    console.print(table)
    success(console, f"Parsed {len(result.recordings)} recording(s). Artifacts directory: {output_dir}")
