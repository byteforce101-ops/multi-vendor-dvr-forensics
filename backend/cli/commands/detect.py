"""dvrforensics detect PATH"""

from __future__ import annotations

from pathlib import Path

import typer
from rich.panel import Panel

from backend.cli.common import require_file
from backend.cli.exit_codes import ExitCode
from backend.cli.theme import error, fact_table, get_console, human_size, section_header

def detect(
    path: Path = typer.Argument(..., help="Path to the evidence file (.dd, .img, .mp4, ...)"),
) -> None:
    """Detect the vendor/parser for an evidence file without fully parsing it."""
    from backend.parsers.registry import ParserManager

    console = get_console()
    section_header(console, "Detect")

    resolved = require_file(path, console)
    size = resolved.stat().st_size

    with console.status("[brand]Scanning file signature...[/brand]", spinner="bouncingBar"):
        parser, confidence, info = ParserManager().detect(str(resolved))

    table = fact_table()
    table.add_row("[field]File:[/field]", f"[path]{resolved}[/path]")
    table.add_row("[field]Size:[/field]", f"{human_size(size)}  [dim]({size:,} bytes)[/dim]")

    if parser is None:
        table.add_row("[field]Result:[/field]", "[err]No matching parser[/err]")
        console.print(Panel(table, border_style="err", title="No Match"))
        error(console, "No registered parser recognized this file.")
        raise typer.Exit(code=ExitCode.UNSUPPORTED_VENDOR)

    table.add_row("", "")
    table.add_row("[field]Detected Vendor:[/field]", f"[ok]{parser.vendor_name}[/ok]")
    table.add_row("[field]Parser:[/field]", type(parser).__name__)
    table.add_row("[field]Parser Version:[/field]", parser.parser_version)
    table.add_row("[field]Confidence:[/field]", f"{confidence * 100:.0f}%")
    if info:
        table.add_row("", "")
        for key, value in info.items():
            table.add_row(f"[dim]{key}:[/dim]", str(value))

    console.print(Panel(table, border_style="brand", title="Detection Result"))
