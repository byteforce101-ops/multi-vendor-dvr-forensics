import typer

<<<<<<< HEAD
=======
from backend.cli import interactive
>>>>>>> 62378bbf9649647cca47b7b00b4599eb368cc53b
from backend.cli.commands import case, detect, evidence
from backend.cli.commands.extract import extract_evidence
from backend.cli.commands.parse import parse_evidence


app = typer.Typer(
    help="DVR Forensics Platform Command Line Interface",
<<<<<<< HEAD
    no_args_is_help=True,
)


=======
    no_args_is_help=False,
)


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """DVR Forensics Platform Command Line Interface."""
    if ctx.invoked_subcommand is None:
        interactive.run()


>>>>>>> 62378bbf9649647cca47b7b00b4599eb368cc53b
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