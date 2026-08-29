"""dvrforensics evidence add|hash|list"""

from __future__ import annotations

import enum
from pathlib import Path

import typer
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)
from rich.table import Table

from backend.cli.common import db_session, require_file
from backend.cli.exit_codes import ExitCode
from backend.cli.theme import error, fact_table, get_console, human_size, section_header, success, warn

app = typer.Typer(help="Register and inspect evidence files.")

DEFAULT_CHUNK_SIZE = 8 * 1024 * 1024  # 8 MiB


class AddMode(str, enum.Enum):
    reference = "reference"
    copy = "copy"


def _hash_progress() -> Progress:
    return Progress(
        SpinnerColumn(style="brand"),
        TextColumn("[field]{task.description}[/field]"),
        BarColumn(bar_width=None, style="brand.dim", complete_style="brand"),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        DownloadColumn(),
        TransferSpeedColumn(),
        TimeRemainingColumn(),
        console=get_console(),
    )


@app.command("hash")
def evidence_hash(
    path: Path = typer.Argument(..., help="Path to the evidence file to hash"),
    chunk_size: int = typer.Option(
        DEFAULT_CHUNK_SIZE, "--chunk-size", help="Read chunk size in bytes (default: 8 MiB)"
    ),
) -> None:
    """Compute MD5 + SHA256 of a file, streamed in chunks (safe for huge images)."""
    from backend.core.integrity.hashing import compute_hashes_with_progress

    console = get_console()
    section_header(console, "Evidence Hash")

    resolved = require_file(path, console)
    total = resolved.stat().st_size

    if chunk_size <= 0:
        error(console, "--chunk-size must be greater than 0")
        raise typer.Exit(code=ExitCode.INVALID_ARGUMENT)

    console.print(f"[field]File:[/field] [path]{resolved}[/path]")
    console.print(f"[field]Size:[/field] {human_size(total)}\n")

    with _hash_progress() as progress:
        task = progress.add_task("Hashing evidence...", total=total)

        def on_progress(done: int, _total: int) -> None:
            progress.update(task, completed=done)

        hashes = compute_hashes_with_progress(
            str(resolved), chunk_size=chunk_size, on_progress=on_progress
        )

    table = fact_table()
    table.add_row("[field]MD5:[/field]", hashes["md5"])
    table.add_row("[field]SHA256:[/field]", hashes["sha256"])
    console.print(Panel(table, border_style="brand", title="Digest"))


@app.command("add")
def evidence_add(
    path: Path = typer.Argument(..., help="Path to the evidence file"),
    case: str = typer.Option(..., "--case", help="Case ID to attach this evidence to"),
    mode: AddMode = typer.Option(
        AddMode.reference,
        "--mode",
        help="reference: register the path in place (no copy, for huge images). "
        "copy: duplicate + hash-verify a forensic working copy.",
    ),
    chunk_size: int = typer.Option(
        DEFAULT_CHUNK_SIZE, "--chunk-size", help="Read chunk size in bytes for hashing (copy mode)"
    ),
) -> None:
    """Register an evidence file against a case."""
    from backend.db.models import Case, EvidenceStatus

    console = get_console()
    section_header(console, "Evidence Add")

    resolved = require_file(path, console)

    with db_session() as db:
        case_row = db.get(Case, case)
        if case_row is None:
            error(console, f"Case not found: {case}")
            raise typer.Exit(code=ExitCode.NOT_FOUND)

        if mode is AddMode.reference:
            from backend.core.acquisition.service import import_evidence_reference

            warn(
                console,
                "Reference mode: the file will NOT be copied. dvrforensics will read it "
                "in place. Make sure the source is mounted read-only or write-blocked.",
            )
            try:
                evidence = import_evidence_reference(db, case, str(resolved))
            except FileNotFoundError:
                error(console, f"File not found: {resolved}")
                raise typer.Exit(code=ExitCode.FILE_NOT_FOUND)

            table = fact_table()
            table.add_row("[field]Evidence ID:[/field]", evidence.id)
            table.add_row("[field]Original path:[/field]", f"[path]{evidence.original_path}[/path]")
            table.add_row("[field]Working copy:[/field]", "[dim](same file — reference mode)[/dim]")
            table.add_row("[field]Status:[/field]", evidence.status.value)
            console.print(Panel(table, border_style="brand", title="Evidence Registered"))
            success(console, "Evidence registered in reference mode.")
            return

        # copy mode
        from backend.core.acquisition.service import import_and_verify_evidence

        total = resolved.stat().st_size
        console.print(f"[field]Creating forensic working copy of:[/field] [path]{resolved}[/path]")
        console.print(
            "[dim]Hashing runs twice in copy mode: once against the original, once "
            "against the copy, so the two can be compared.[/dim]\n"
        )

        with _hash_progress() as progress:
            task = progress.add_task("Hashing + copying...", total=total * 2)
            calls = {"n": 0}

            def on_progress(done: int, _total: int) -> None:
                # Two hashing passes (source, then working copy) share one bar.
                progress.update(task, completed=calls["n"] * total + done)

            try:
                evidence, matched = import_and_verify_evidence(
                    db, case, str(resolved), chunk_size=chunk_size, on_progress=on_progress
                )
            except FileNotFoundError:
                error(console, f"File not found: {resolved}")
                raise typer.Exit(code=ExitCode.FILE_NOT_FOUND)
            finally:
                calls["n"] = 1
            progress.update(task, completed=total * 2)

        table = fact_table()
        table.add_row("[field]Evidence ID:[/field]", evidence.id)
        table.add_row("[field]Original path:[/field]", f"[path]{evidence.original_path}[/path]")
        table.add_row("[field]Working copy:[/field]", f"[path]{evidence.working_copy_path}[/path]")
        table.add_row("[field]SHA256:[/field]", evidence.sha256)
        table.add_row("[field]MD5:[/field]", evidence.md5)
        table.add_row(
            "[field]Status:[/field]",
            f"[ok]{evidence.status.value}[/ok]" if matched else f"[err]{evidence.status.value}[/err]",
        )
        console.print(Panel(table, border_style="brand" if matched else "err", title="Evidence Registered"))

        if matched:
            success(console, "Working copy verified — hashes match the original.")
        else:
            error(console, "TAMPER WARNING: working copy hash does NOT match the original.")
            raise typer.Exit(code=ExitCode.CORRUPTED_EVIDENCE)


@app.command("list")
def evidence_list(
    case: str = typer.Option(..., "--case", help="Case ID to list evidence for"),
) -> None:
    """List evidence registered against a case."""
    from backend.db.models import Case, Evidence

    console = get_console()
    section_header(console, "Evidence List")

    with db_session() as db:
        case_row = db.get(Case, case)
        if case_row is None:
            error(console, f"Case not found: {case}")
            raise typer.Exit(code=ExitCode.NOT_FOUND)

        items = db.query(Evidence).filter(Evidence.case_id == case).all()

        if not items:
            warn(console, f"No evidence registered for case {case}.")
            return

        table = Table(border_style="brand.dim", header_style="brand")
        table.add_column("Evidence ID", no_wrap=True)
        table.add_column("Filename")
        table.add_column("Vendor")
        table.add_column("Status")
        table.add_column("SHA256", no_wrap=True)
        table.add_column("Acquired At")

        for ev in items:
            status_style = "ok" if ev.status.value == "verified" else (
                "err" if ev.status.value == "tampered" else "dim"
            )
            table.add_row(
                ev.id,
                ev.original_filename,
                ev.vendor or "[dim]-[/dim]",
                f"[{status_style}]{ev.status.value}[/{status_style}]",
                (ev.sha256 or "-")[:16] + ("…" if ev.sha256 else ""),
                ev.acquired_at.isoformat(sep=" ", timespec="seconds"),
            )

        console.print(table)
