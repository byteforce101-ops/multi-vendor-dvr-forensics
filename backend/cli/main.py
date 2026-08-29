"""dvrforensics — local-first CLI for the DVR Forensics Platform.

This module only wires Typer sub-apps together and handles top-level error
presentation. All forensic logic lives in backend/core, backend/parsers,
backend/video, backend/ai, and backend/db, exactly as it did before the CLI
existed — nothing here duplicates that logic.
"""

from __future__ import annotations

import os

import typer
from click.exceptions import ClickException

from backend.cli.commands import analyze, case, detect, evidence, extract, parse, search
from backend.cli.exit_codes import ExitCode
from backend.cli.theme import error, get_console, print_banner

app = typer.Typer(
    name="dvrforensics",
    help="Local-first forensic CLI for DVR evidence: detect, hash, parse, extract, "
    "manage cases, run AI video analysis, and search — all without a running server.",
    no_args_is_help=False,
    add_completion=True,
    rich_markup_mode="rich",
    # The [project.scripts] entry point (backend.cli.main:app) invokes this
    # Typer instance directly, so any exception a command doesn't handle
    # itself falls through to Typer's own handler rather than run()'s below
    # — keep that fallback terse instead of a full raw Python traceback.
    pretty_exceptions_show_locals=False,
    pretty_exceptions_short=True,
)

app.add_typer(case.app, name="case")
app.add_typer(evidence.app, name="evidence")

# detect/parse/extract/analyze/search are single commands, not command
# groups — register the functions directly rather than mounting them as
# nested Typer sub-apps (a sub-app with only a callback still behaves like
# a group expecting a further COMMAND argument).
app.command("detect")(detect.detect)
app.command("parse")(parse.parse)
app.command("extract")(extract.extract)
app.command("analyze")(analyze.analyze)
app.command("search")(search.search)

@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    # Ensure .env is loaded for every invocation, not just the ones that
    # happen to touch a DB session — GROQ_API_KEY and friends live there.
    from backend.config.settings import get_settings
    get_settings()

    if ctx.invoked_subcommand is None:
        from backend.cli import interactive
        interactive.run()
        raise typer.Exit(code=ExitCode.OK)

def run() -> None:
    """Entry point used by pyproject.toml's [project.scripts]."""
    debug = os.environ.get("DVRFORENSICS_DEBUG", "").lower() in ("1", "true", "yes")
    try:
        app()
    except typer.Exit:
        raise
    except ClickException:
        raise
    except KeyboardInterrupt:
        get_console().print("\n[dim]Interrupted.[/dim]")
        raise typer.Exit(code=ExitCode.GENERAL_ERROR)
    except Exception as exc:  # last-resort guard: never dump a raw traceback at users
        console = get_console()
        if debug:
            console.print_exception(show_locals=False)
        else:
            error(console, f"Unexpected error: {exc}")
            console.print("[dim]Set DVRFORENSICS_DEBUG=1 to see the full traceback.[/dim]")
        raise typer.Exit(code=ExitCode.GENERAL_ERROR)


if __name__ == "__main__":
    run()
