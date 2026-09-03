import sys
from typing import Optional

import typer

from backend.cli import interactive
from backend.cli.commands import case, detect, evidence
from backend.cli.commands.analyze import analyze
from backend.cli.commands.extract import extract_evidence
from backend.cli.commands.parse import parse_evidence
from backend.cli.commands.search import search


app = typer.Typer(
    help="TraceX DVR Forensics Platform Command Line Interface",
    no_args_is_help=False,
)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    file: Optional[str] = typer.Option(
        None,
        "--file",
        "-f",
        help="Evidence or video file path to analyze in the TUI.",
    ),
    query: Optional[str] = typer.Option(
        None,
        "--query",
        "-q",
        help="Execute a one-shot query from the command line without launching the full TUI.",
    ),
    case_id: Optional[str] = typer.Option(
        None,
        "--case",
        "-c",
        help="Case ID for the query.",
    ),
    pipeline_mode: bool = typer.Option(
        False,
        "--pipeline",
        help="Run the classic guided file wizard (detect -> parse -> extract -> analyze).",
    ),
    tui_mode: bool = typer.Option(
        False,
        "--tui",
        help="Force launch the full-screen interactive TUI.",
    ),
):
    """TraceX DVR Forensics Platform Command Line Interface."""
    if ctx.invoked_subcommand is None:
        if query:
            from backend.cli.tui.engine import TraceXPipelineEngine
            from rich.console import Console

            console = Console()
            engine = TraceXPipelineEngine()
            if file:
                engine.run_pipeline(file)
            ans = engine.ask_video_query(query)
            console.print(f"[bold bright_cyan]TraceX Findings ({ans.source}):[/bold bright_cyan]\n")
            console.print(ans.answer)
            return

        if pipeline_mode:
            interactive.run()
            return

        is_tty = hasattr(sys.stdin, "isatty") and sys.stdin.isatty() and hasattr(sys.stdout, "isatty") and sys.stdout.isatty()
        if not is_tty and not tui_mode:
            # Non-interactive environment or test runner (e.g. Typer CliRunner)
            from backend.cli.theme import get_console

            console = get_console()
            interactive.print_tracex_banner(console)
            console.print(
                "TraceX DVR Forensics Platform CLI.\n"
                "Run in an interactive terminal to launch the full-screen TUI, or use --help to list subcommands."
            )
            return

        from backend.cli.tui.app import run_tui

        run_tui(default_file_path=file)


# =========================================================
# SUBCOMMANDS
# =========================================================

@app.command(
    "tui",
    help="Launch the full-screen TraceX interactive Terminal User Interface.",
)
def tui_cmd(
    file: Optional[str] = typer.Option(None, "--file", "-f", help="Evidence or video file path to analyze"),
    query: Optional[str] = typer.Option(None, "--query", "-q", help="Initial query to execute in TUI"),
):
    from backend.cli.tui.app import run_tui

    run_tui(default_file_path=file, initial_query=query)


@app.command(
    "pipeline",
    help="Run the classic guided step-by-step file analysis wizard.",
)
def pipeline_cmd():
    interactive.run()


app.add_typer(
    case.app,
    name="case",
)

app.add_typer(
    evidence.app,
    name="evidence",
)

app.command(
    "detect",
    help="Detect the DVR vendor and parser for an evidence file.",
)(
    detect.detect
)

app.command(
    "parse",
    help="Parse DVR evidence and discover recordings.",
)(
    parse_evidence
)

app.command(
    "extract",
    help="Extract recoverable recordings from DVR evidence.",
)(
    extract_evidence
)

app.command(
    "analyze",
    help="Run video analysis, AI event reconstruction and forensic summary.",
)(
    analyze
)

app.command(
    "search",
    help="Interpret a natural-language query into a filter, then list matching events.",
)(
    search
)


if __name__ == "__main__":
    app()