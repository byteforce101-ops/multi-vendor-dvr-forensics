from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from backend.parsers.registry import ParserManager

console = Console()


def parse_evidence(
    evidence_path: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
        help="Path to the evidence file.",
    ),
    output: Path = typer.Option(
        Path("./output"),
        "--output",
        "-o",
        help="Directory for parser output.",
    ),
):
    output.mkdir(parents=True, exist_ok=True)

    console.print(
        Panel.fit(
            "[bold cyan]DVR FORENSICS PLATFORM[/bold cyan]\n"
            "Evidence Parsing",
            border_style="cyan",
        )
    )

    console.print(f"[bold cyan]Evidence:[/bold cyan] {evidence_path}")
    console.print(f"[bold cyan]Output:[/bold cyan] {output.resolve()}")

    console.print("\n[cyan]Detecting and parsing evidence...[/cyan]\n")

    manager = ParserManager()

    try:
        result = manager.parse(
            str(evidence_path),
            str(output.resolve()),
        )
    except Exception as exc:
        console.print(
            Panel(
                f"[bold red]Unexpected parsing failure[/bold red]\n\n{exc}",
                border_style="red",
            )
        )
        raise typer.Exit(code=1)

    if not result.success:
        console.print(
            Panel(
                "[bold red]Parsing failed[/bold red]",
                border_style="red",
            )
        )

        if result.error_code:
            console.print(
                f"[bold red]Error Code:[/bold red] {result.error_code}"
            )

        if result.errors:
            console.print("\n[bold red]Errors:[/bold red]")

            for error in result.errors:
                console.print(f"  [red]•[/red] {error}")

        if result.warnings:
            console.print("\n[bold yellow]Warnings:[/bold yellow]")

            for warning in result.warnings:
                console.print(f"  [yellow]•[/yellow] {warning}")

        raise typer.Exit(code=1)

    summary = Table(title="Parse Summary")

    summary.add_column("Property", style="bold cyan")
    summary.add_column("Value")

    summary.add_row("Vendor", result.vendor)
    summary.add_row("Parser Version", result.parser_version)
    summary.add_row(
        "Recordings Found",
        str(len(result.recordings)),
    )

    console.print(summary)

    if result.warnings:
        console.print("\n[bold yellow]Warnings:[/bold yellow]")

        for warning in result.warnings:
            console.print(f"  [yellow]•[/yellow] {warning}")

    if result.recordings:

        table = Table(
            title="Discovered Recordings",
            show_lines=True,
        )

        table.add_column("Recording ID", style="cyan")
        table.add_column("Camera ID")
        table.add_column("Timestamp")
        table.add_column("Duration")
        table.add_column("Resolution")
        table.add_column("Codec")
        table.add_column("Status")

        for recording in result.recordings:

            timestamp_value = (
                recording.normalized_timestamp
                or recording.original_timestamp
            )

            timestamp = (
                str(timestamp_value)
                if timestamp_value
                else "Unknown"
            )

            duration = (
                f"{recording.duration_seconds:.2f}s"
                if recording.duration_seconds is not None
                else "Unknown"
            )

            resolution = (
                recording.resolution
                if recording.resolution
                else "Unknown"
            )

            codec = (
                recording.codec
                if recording.codec
                else "Unknown"
            )

            table.add_row(
                str(recording.recording_id),
                str(recording.camera_id),
                timestamp,
                duration,
                resolution,
                codec,
                str(recording.recovery_status),
            )

        console.print()
        console.print(table)

    console.print(
        "\n[bold green]✓ Parsing completed successfully.[/bold green]"
    )