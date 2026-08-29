from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from backend.parsers.registry import ParserManager

app = typer.Typer(
    help="Detect the DVR vendor and parser for an evidence file."
)

console = Console()


@app.callback(invoke_without_command=True)
def detect(
    ctx: typer.Context,
    evidence_path: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
        help="Path to the evidence file.",
    ),
):
    if ctx.invoked_subcommand is not None:
        return

    console.print(
        Panel.fit(
            "[bold cyan]DVR FORENSICS PLATFORM[/bold cyan]\n"
            "Evidence Detection",
            border_style="cyan",
        )
    )

    manager = ParserManager()

    try:
        parser, confidence, info = manager.detect(str(evidence_path))
    except Exception as exc:
        console.print(f"[bold red]Detection failed:[/bold red] {exc}")
        raise typer.Exit(code=1)

    file_table = Table(show_header=False, box=None)
    file_table.add_column(style="bold cyan")
    file_table.add_column()

    file_table.add_row("File", evidence_path.name)
    file_table.add_row("Path", str(evidence_path))
    file_table.add_row(
        "Size",
        f"{evidence_path.stat().st_size:,} bytes",
    )

    console.print(file_table)
    console.print()

    if parser is None:
        console.print(
            Panel(
                "[yellow]No supported parser detected for this evidence file.[/yellow]",
                title="Detection Result",
                border_style="yellow",
            )
        )
        raise typer.Exit(code=2)

    result_table = Table(
        title="Detection Result",
        show_header=True,
    )

    result_table.add_column("Property", style="bold cyan")
    result_table.add_column("Value")

    result_table.add_row("Vendor", parser.vendor_name)
    result_table.add_row("Parser", parser.__class__.__name__)
    result_table.add_row("Version", parser.parser_version)
    result_table.add_row("Confidence", f"{confidence:.1%}")

    console.print(result_table)

    if info:
        metadata_table = Table(
            title="Detection Metadata",
            show_header=True,
        )

        metadata_table.add_column("Key", style="cyan")
        metadata_table.add_column("Value")

        for key, value in info.items():
            metadata_table.add_row(str(key), str(value))

        console.print(metadata_table)

    console.print(
        "\n[bold green]✓ Supported evidence format detected.[/bold green]"
    )