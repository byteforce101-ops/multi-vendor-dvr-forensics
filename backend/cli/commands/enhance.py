"""backend/cli/commands/enhance.py

CLI command for forensic video enhancement.
"""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from backend.video.enhancement.preprocessor import enhance_video_file

app = typer.Typer(help="Enhance CCTV video footage using TraceX Forensic Enhancement.")
console = Console()


@app.callback(invoke_without_command=True)
def enhance_cmd(
    ctx: typer.Context,
    video_path: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
        help="Path to the input video file.",
    ),
    output_path: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Destination path for the enhanced video file. Defaults to <name>_enhanced.mp4.",
    ),
    clahe: bool = typer.Option(
        True,
        "--clahe/--no-clahe",
        help="Enable/disable Contrast Limited Adaptive Histogram Equalization (CLAHE).",
    ),
    gamma: bool = typer.Option(
        True,
        "--gamma/--no-gamma",
        help="Enable/disable dynamic exposure auto-gamma correction.",
    ),
    sharpen: bool = typer.Option(
        True,
        "--sharpen/--no-sharpen",
        help="Enable/disable unsharp mask edge enhancement.",
    ),
    clip_limit: float = typer.Option(
        2.8,
        "--clip-limit",
        help="CLAHE contrast clip limit.",
    ),
    sharpen_strength: float = typer.Option(
        0.6,
        "--sharpen-strength",
        help="Edge sharpening strength coefficient.",
    ),
):
    if ctx.invoked_subcommand is not None:
        return

    console.print(
        Panel.fit(
            "[bold cyan]TRACEX FORENSICS ENGINE[/bold cyan]\n"
            "Surveillance Video Enhancement",
            border_style="cyan",
        )
    )

    if output_path is None:
        output_path = video_path.parent / f"{video_path.stem}_enhanced.mp4"

    console.print(f"[cyan]Input Video:[/]  {video_path}")
    console.print(f"[cyan]Output Video:[/] {output_path}")
    console.print(
        f"[dim]Parameters: CLAHE={clahe} (clip={clip_limit}) | AutoGamma={gamma} | Sharpen={sharpen} (strength={sharpen_strength})[/dim]\n"
    )

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold cyan]{task.description}[/bold cyan]"),
        console=console,
    ) as progress:
        task = progress.add_task("Enhancing video frames with TraceX engine...", total=None)
        try:
            out_file = enhance_video_file(
                input_path=video_path,
                output_path=output_path,
                enable_clahe=clahe,
                auto_gamma=gamma,
                enable_sharpen=sharpen,
                clahe_clip_limit=clip_limit,
                sharpen_strength=sharpen_strength,
            )
            progress.update(task, completed=True, description="Enhancement completed successfully!")
        except Exception as exc:
            console.print(f"[bold red]Enhancement failed:[/bold red] {exc}")
            raise typer.Exit(code=1)

    console.print(f"\n[bold green]✓ Enhanced video saved to:[/] [bold]{out_file}[/bold]")
