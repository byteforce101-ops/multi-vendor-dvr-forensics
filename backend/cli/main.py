import typer

from backend.cli import interactive
from backend.cli.commands import case, detect, evidence
from backend.cli.commands.extract import extract_evidence
from backend.cli.commands.parse import parse_evidence


app = typer.Typer(
    help="DVR Forensics Platform Command Line Interface",
    no_args_is_help=False,
)


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """DVR Forensics Platform Command Line Interface."""
    if ctx.invoked_subcommand is None:
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


if __name__ == "__main__":
    app()