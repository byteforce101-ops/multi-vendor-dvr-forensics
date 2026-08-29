import hashlib
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    TextColumn,
    TimeRemainingColumn,
)
from rich.table import Table

from backend.core.acquisition.service import (
    hash_evidence as hash_stored_evidence,
    import_evidence,
    reference_evidence,
)
from backend.db.database import SessionLocal
from backend.db.models import Case, Evidence

app = typer.Typer(
    help="Evidence management commands.",
    no_args_is_help=True,
)

console = Console()

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
):
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
                while chunk := file.read(CHUNK_SIZE):
                    sha256.update(chunk)
                    md5.update(chunk)

                    progress.update(
                        task,
                        advance=len(chunk),
                    )

        except OSError as exc:
            console.print(
                f"[bold red]Unable to read evidence:[/bold red] {exc}"
            )
            raise typer.Exit(code=1)

    console.print()
    console.print(
        "[bold green]Hashing completed successfully.[/bold green]"
    )

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
    case_id: str = typer.Option(
        ...,
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
    mode = mode.lower()

    if mode not in {"reference", "copy"}:
        console.print(
            "[bold red]Invalid mode.[/bold red] "
            "Use 'reference' or 'copy'."
        )
        raise typer.Exit(code=1)

    console.print(
        Panel.fit(
            "[bold cyan]DVR FORENSICS PLATFORM[/bold cyan]\n"
            "Evidence Acquisition",
            border_style="cyan",
        )
    )

    console.print(
        f"[bold cyan]File:[/bold cyan] {evidence_path}"
    )
    console.print(
        f"[bold cyan]Mode:[/bold cyan] {mode}"
    )
    console.print(
        f"[bold cyan]Case ID:[/bold cyan] {case_id}"
    )

    db = SessionLocal()

    try:
        case = (
            db.query(Case)
            .filter(Case.id == case_id)
            .one_or_none()
        )

        if case is None:
            console.print(
                "\n[bold red]Case not found.[/bold red]"
            )
            raise typer.Exit(code=1)

        if mode == "reference":
            console.print(
                "\n[cyan]Registering evidence without copying the original...[/cyan]"
            )

            evidence = reference_evidence(
                db,
                case_id,
                str(evidence_path),
            )

        else:
            console.print(
                "\n[yellow]Copying evidence into managed storage...[/yellow]"
            )

            evidence = import_evidence(
                db,
                case_id,
                str(evidence_path),
            )

        console.print(
            "\n[cyan]Calculating cryptographic hashes...[/cyan]"
        )

        evidence = hash_stored_evidence(
            db,
            evidence,
        )

        table = Table(
            title="Evidence Registered Successfully"
        )

        table.add_column(
            "Property",
            style="bold cyan",
        )
        table.add_column("Value")

        table.add_row(
            "Evidence ID",
            evidence.id,
        )

        table.add_row(
            "Case ID",
            evidence.case_id,
        )

        table.add_row(
            "Filename",
            evidence.original_filename,
        )

        table.add_row(
            "Mode",
            mode,
        )

        table.add_row(
            "Original Path",
            evidence.original_path,
        )

        table.add_row(
            "Working Path",
            evidence.working_copy_path,
        )

        table.add_row(
            "SHA-256",
            evidence.sha256 or "Not available",
        )

        table.add_row(
            "MD5",
            evidence.md5 or "Not available",
        )

        table.add_row(
            "Status",
            evidence.status.value,
        )

        console.print()
        console.print(table)

        console.print(
            "\n[bold green]✓ Evidence registered successfully.[/bold green]"
        )

    except FileNotFoundError as exc:
        console.print(
            f"\n[bold red]File not found:[/bold red] {exc}"
        )
        raise typer.Exit(code=1)

    except typer.Exit:
        raise

    except Exception as exc:
        db.rollback()

        console.print(
            f"\n[bold red]Evidence acquisition failed:[/bold red] {exc}"
        )

        raise typer.Exit(code=1)

    finally:
        db.close()


@app.command("info")
def evidence_info(
    evidence_id: str = typer.Argument(
        ...,
        help="ID of the evidence record.",
    ),
):
    db = SessionLocal()

    try:
        evidence = (
            db.query(Evidence)
            .filter(Evidence.id == evidence_id)
            .one_or_none()
        )

        if evidence is None:
            console.print(
                "[bold red]Evidence not found.[/bold red]"
            )
            raise typer.Exit(code=1)

        table = Table(title="Evidence Information")

        table.add_column(
            "Property",
            style="bold cyan",
        )
        table.add_column("Value")

        table.add_row(
            "Evidence ID",
            evidence.id,
        )

        table.add_row(
            "Case ID",
            evidence.case_id,
        )

        table.add_row(
            "Filename",
            evidence.original_filename,
        )

        table.add_row(
            "Original Path",
            evidence.original_path,
        )

        table.add_row(
            "Working Path",
            evidence.working_copy_path,
        )

        table.add_row(
            "SHA-256",
            evidence.sha256 or "Not calculated",
        )

        table.add_row(
            "MD5",
            evidence.md5 or "Not calculated",
        )

        table.add_row(
            "Vendor",
            evidence.vendor or "Not detected",
        )

        table.add_row(
            "Parser Version",
            evidence.parser_version or "Not available",
        )

        table.add_row(
            "Status",
            evidence.status.value,
        )

        table.add_row(
            "Acquired",
            str(evidence.acquired_at),
        )

        console.print()
        console.print(table)

    except typer.Exit:
        raise

    except Exception as exc:
        console.print(
            f"\n[bold red]Failed to retrieve evidence:[/bold red] {exc}"
        )
        raise typer.Exit(code=1)

    finally:
        db.close()