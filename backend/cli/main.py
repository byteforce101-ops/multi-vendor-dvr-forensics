import typer

from backend.cli.commands import case, detect, evidence
from backend.cli.commands.extract import extract_evidence
from backend.cli.commands.parse import parse_evidence


app = typer.Typer(
    help="DVR Forensics Platform Command Line Interface",
    no_args_is_help=True,
)


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