from pathlib import Path
import shutil

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from backend.cli.exit_codes import ExitCode
from backend.cli.theme import get_console
from backend.parsers.registry import ParserManager

console = get_console()


def extract_evidence(
    evidence_path: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
        help="Path to the DVR evidence file.",
    ),
    output: Path = typer.Option(
        Path("./output/recovered"),
        "--output",
        "-o",
        help="Directory where recovered recordings will be saved.",
    ),
):
    console.print(
        Panel.fit(
            "[bold cyan]DVR FORENSICS PLATFORM[/bold cyan]\n"
            "Evidence Extraction",
            border_style="cyan",
        )
    )

    console.print(
        f"[bold cyan]Evidence:[/bold cyan] {evidence_path}"
    )

    console.print(
        f"[bold cyan]Output:[/bold cyan] {output.resolve()}"
    )

    if shutil.which("ffmpeg") is None:
        console.print(
            Panel(
                "[bold red]ffmpeg was not found on PATH.[/bold red]\n\n"
                "Hikvision recording extraction requires ffmpeg for "
                "MPEG-PS/TS to MP4 muxing.",
                title="Missing Dependency",
                border_style="red",
            )
        )
        raise typer.Exit(code=ExitCode.MISSING_DEPENDENCY)

    output.mkdir(parents=True, exist_ok=True)

    manager = ParserManager()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:

        task = progress.add_task(
            "Parsing evidence...",
            total=None,
        )

        try:
            parse_result = manager.parse(
                str(evidence_path),
                str(output),
            )
        except Exception as exc:
            console.print(
                f"[bold red]Parsing failed:[/bold red] {exc}"
            )
            raise typer.Exit(code=1)

        if not parse_result.success:
            console.print(
                Panel(
                    "[bold red]Evidence parsing failed.[/bold red]",
                    border_style="red",
                )
            )

            if parse_result.errors:
                for error in parse_result.errors:
                    console.print(f"[red]• {error}[/red]")

            raise typer.Exit(code=1)

        progress.update(
            task,
            description=(
                f"Extracting {len(parse_result.recordings)} recording(s)..."
            ),
        )

        try:
            extraction_result = manager.extract(
                str(evidence_path),
                str(output),
                parse_result,
            )
        except Exception as exc:
            console.print(
                f"[bold red]Extraction failed:[/bold red] {exc}"
            )
            raise typer.Exit(code=1)

    recovered = [
        recording
        for recording in extraction_result.recordings
        if recording.extracted_path
    ]

    partial = [
        recording
        for recording in extraction_result.recordings
        if recording.recovery_status == "PARTIAL"
    ]

    summary = Table(title="Extraction Summary")

    summary.add_column("Property", style="bold cyan")
    summary.add_column("Value")

    summary.add_row(
        "Vendor",
        extraction_result.vendor,
    )

    summary.add_row(
        "Recordings Found",
        str(len(parse_result.recordings)),
    )

    summary.add_row(
        "Successfully Extracted",
        str(len(recovered)),
    )

    summary.add_row(
        "Partial / Skipped",
        str(len(partial)),
    )

    summary.add_row(
        "Output Directory",
        str(output.resolve()),
    )

    console.print()
    console.print(summary)

    if extraction_result.recordings:
        recordings_table = Table(
            title="Extracted / Recovered Recordings",
            show_lines=True,
        )

        recordings_table.add_column(
            "Recording ID",
            style="cyan",
        )
        recordings_table.add_column("Camera")
        recordings_table.add_column("Status")
        recordings_table.add_column("Output File")

        for recording in extraction_result.recordings:
            recordings_table.add_row(
                str(recording.recording_id),
                str(recording.camera_id),
                str(recording.recovery_status),
                str(recording.extracted_path or "Not extracted / partial"),
            )

        console.print()
        console.print(recordings_table)

    if extraction_result.warnings:
        console.print("\n[bold yellow]Warnings:[/bold yellow]")

        for warning in extraction_result.warnings:
            console.print(
                f"  [yellow]•[/yellow] {warning}"
            )

    if extraction_result.errors:
        console.print("\n[bold red]Errors:[/bold red]")

        for error in extraction_result.errors:
            console.print(
                f"  [red]•[/red] {error}"
            )

    if not extraction_result.success:
        console.print(
            "\n[bold red]✗ Extraction completed with errors.[/bold red]"
        )
        raise typer.Exit(code=1)

    if len(recovered) == 0:
        console.print(
            "\n[bold yellow]⚠ Extraction completed, but no recordings could be recovered.[/bold yellow]"
        )
        return

    if partial:
        console.print(
            "\n[bold yellow]⚠ Extraction completed with partial or skipped recordings.[/bold yellow]"
        )
        return

    console.print(
        "\n[bold green]✓ Extraction completed successfully.[/bold green]"
    )