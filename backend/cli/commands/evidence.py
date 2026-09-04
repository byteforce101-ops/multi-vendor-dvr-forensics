import hashlib
from pathlib import Path
from typing import Optional

import typer
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    TextColumn,
    TimeRemainingColumn,
)
from rich.table import Table

from backend.cli.common import db_session
from backend.cli.exit_codes import ExitCode
from backend.cli.theme import get_console, error, warn, success
from backend.core.acquisition.service import (
    hash_evidence as hash_stored_evidence,
    import_evidence,
    reference_evidence,
)
from backend.db.models import Case, Evidence

app = typer.Typer(
    help="Evidence management commands.",
    no_args_is_help=True,
)

console = get_console()

CHUNK_SIZE = 8 * 1024 * 1024


@app.command("hash")
def hash_evidence(
    evidence_path: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
        help="Path to the evidence file.",
    ),
    chunk_size: int = typer.Option(
        CHUNK_SIZE,
        "--chunk-size",
        help="Chunk size in bytes for reading.",
    ),
):
    if chunk_size <= 0:
        error(console, "Chunk size must be greater than 0.")
        raise typer.Exit(code=ExitCode.INVALID_ARGUMENT)

    sha256 = hashlib.sha256()
    md5 = hashlib.md5()

    total_size = evidence_path.stat().st_size

    console.print(
        f"\n[bold cyan]Hashing:[/bold cyan] {evidence_path.name}"
    )
    console.print(
        f"[bold cyan]Size:[/bold cyan] {total_size:,} bytes\n"
    )

    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.percentage:>3.0f}%"),
        TimeRemainingColumn(),
        console=console,
    ) as progress:

        task = progress.add_task(
            "Calculating hashes",
            total=total_size,
        )

        try:
            with evidence_path.open("rb") as file:
                while chunk := file.read(chunk_size):
                    sha256.update(chunk)
                    md5.update(chunk)

                    progress.update(
                        task,
                        advance=len(chunk),
                    )

        except OSError as exc:
            error(console, f"Unable to read evidence: {exc}")
            raise typer.Exit(code=ExitCode.GENERAL_ERROR)

    console.print()
    success(console, "Hashing completed successfully.")

    console.print(
        f"\n[bold cyan]MD5:[/bold cyan]\n{md5.hexdigest()}"
    )

    console.print(
        f"\n[bold cyan]SHA256:[/bold cyan]\n{sha256.hexdigest()}"
    )


@app.command("add")
def add_evidence(
    evidence_path: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
        help="Path to the evidence file.",
    ),
    case: Optional[str] = typer.Option(
        None,
        "--case",
        help="ID of the case this evidence belongs to.",
    ),
    case_id: Optional[str] = typer.Option(
        None,
        "--case-id",
        "-c",
        help="ID of the case this evidence belongs to.",
    ),
    mode: str = typer.Option(
        "reference",
        "--mode",
        "-m",
        help="Acquisition mode: reference or copy.",
    ),
):
    target_case_id = case or case_id
    if not target_case_id:
        error(console, "--case or --case-id is required.")
        raise typer.Exit(code=ExitCode.INVALID_ARGUMENT)

    mode = mode.lower()
    if mode not in {"reference", "copy"}:
        error(console, "Invalid mode. Use 'reference' or 'copy'.")
        raise typer.Exit(code=ExitCode.INVALID_ARGUMENT)

    console.print(
        Panel.fit(
            "[bold cyan]DVR FORENSICS PLATFORM[/bold cyan]\n"
            "Evidence Acquisition",
            border_style="cyan",
        )
    )

    console.print(f"[bold cyan]File:[/bold cyan] {evidence_path}")
    console.print(f"[bold cyan]Mode:[/bold cyan] {mode}")
    console.print(f"[bold cyan]Case ID:[/bold cyan] {target_case_id}")

    with db_session() as db:
        case_obj = (
            db.query(Case)
            .filter(Case.id == target_case_id)
            .one_or_none()
        )

        if case_obj is None:
            error(console, "Case not found.")
            raise typer.Exit(code=ExitCode.NOT_FOUND)

        if mode == "reference":
            console.print("\n[cyan]Registering evidence in reference mode (without copying)...[/cyan]")
            evidence = reference_evidence(
                db,
                target_case_id,
                str(evidence_path),
            )
        else:
            console.print("\n[yellow]Copying evidence into managed storage...[/yellow]")
            evidence = import_evidence(
                db,
                target_case_id,
                str(evidence_path),
            )

        console.print("\n[cyan]Calculating cryptographic hashes...[/cyan]")
        evidence = hash_stored_evidence(
            db,
            evidence,
        )

        if mode == "copy":
            from backend.core.acquisition.service import verify_evidence
            evidence = verify_evidence(
                db,
                evidence,
            )

        table = Table(title="Evidence Registered Successfully")
        table.add_column("Property", style="bold cyan")
        table.add_column("Value")

        table.add_row("Evidence ID", evidence.id)
        table.add_row("Case ID", evidence.case_id)
        table.add_row("Filename", evidence.original_filename)
        table.add_row("Mode", mode)
        table.add_row("Original Path", evidence.original_path)
        table.add_row("Working Path", evidence.working_copy_path)
        table.add_row("SHA-256", evidence.sha256 or "Not available")
        table.add_row("MD5", evidence.md5 or "Not available")
        table.add_row("Status", evidence.status.value)

        console.print()
        console.print(table)
        success(console, f"Evidence registered and verified successfully in {mode} mode.")


@app.command("list")
def list_evidence(
    case: Optional[str] = typer.Option(
        None,
        "--case",
        "--case-id",
        "-c",
        help="Filter evidence by case ID.",
    ),
):
    with db_session() as db:
        query = db.query(Evidence)
        if case:
            query = query.filter(Evidence.case_id == case)
        items = query.order_by(Evidence.acquired_at.desc()).all()

        if not items:
            warn(console, "No evidence items found.")
            return

        table = Table(title="Evidence Items")
        table.add_column("Evidence ID", style="cyan")
        table.add_column("Filename")
        table.add_column("Case ID")
        table.add_column("Vendor")
        table.add_column("Status")
        table.add_column("Acquired")

        for item in items:
            table.add_row(
                item.id,
                item.original_filename,
                item.case_id,
                item.vendor or "Unknown",
                item.status.value,
                str(item.acquired_at),
            )

        console.print(table)


@app.command("info")
def evidence_info(
    evidence_id: str = typer.Argument(
        ...,
        help="ID of the evidence record.",
    ),
):
    with db_session() as db:
        evidence = (
            db.query(Evidence)
            .filter(Evidence.id == evidence_id)
            .one_or_none()
        )

        if evidence is None:
            error(console, "Evidence not found.")
            raise typer.Exit(code=ExitCode.NOT_FOUND)

        table = Table(title="Evidence Information")
        table.add_column("Property", style="bold cyan")
        table.add_column("Value")

        table.add_row("Evidence ID", evidence.id)
        table.add_row("Case ID", evidence.case_id)
        table.add_row("Filename", evidence.original_filename)
        table.add_row("Original Path", evidence.original_path)
        table.add_row("Working Path", evidence.working_copy_path)
        table.add_row("SHA-256", evidence.sha256 or "Not calculated")
        table.add_row("MD5", evidence.md5 or "Not calculated")
        table.add_row("Vendor", evidence.vendor or "Not detected")
        table.add_row("Parser Version", evidence.parser_version or "Not available")
        table.add_row("Status", evidence.status.value)
        table.add_row("Acquired", str(evidence.acquired_at))

        console.print(table)