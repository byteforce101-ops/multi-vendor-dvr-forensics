"""dvrforensics case create|list|show"""

from __future__ import annotations

from typing import Optional

import typer
from rich.panel import Panel
from rich.table import Table

from backend.cli.common import db_session
from backend.cli.exit_codes import ExitCode
from backend.cli.theme import error, fact_table, get_console, section_header, success

app = typer.Typer(help="Manage forensic cases.")


@app.command("create")
def case_create(
    name: str = typer.Option(..., "--name", help="Case name"),
    investigator: str = typer.Option(..., "--investigator", help="Investigator name"),
    case_number: Optional[str] = typer.Option(None, "--case-number", help="External case number"),
    description: Optional[str] = typer.Option(None, "--description", help="Free-text description"),
) -> None:
    """Create a new case."""
    from backend.db.models import Case

    console = get_console()
    section_header(console, "Case Create")

    with db_session() as db:
        case = Case(
            name=name,
            investigator=investigator,
            case_number=case_number,
            description=description,
        )
        db.add(case)
        db.commit()
        db.refresh(case)

        table = fact_table()
        table.add_row("[field]Case ID:[/field]", case.id)
        table.add_row("[field]Name:[/field]", case.name)
        table.add_row("[field]Investigator:[/field]", case.investigator)
        table.add_row("[field]Case Number:[/field]", case.case_number or "[dim]-[/dim]")
        table.add_row("[field]Status:[/field]", case.status)
        console.print(Panel(table, border_style="brand", title="Case Created"))
        success(console, f"Created case {case.id}")


@app.command("list")
def case_list() -> None:
    """List all cases."""
    from backend.db.models import Case

    console = get_console()
    section_header(console, "Case List")

    with db_session() as db:
        cases = db.query(Case).order_by(Case.created_at.desc()).all()

        if not cases:
            console.print("[dim]No cases yet. Create one with `dvrforensics case create`.[/dim]")
            return

        table = Table(border_style="brand.dim", header_style="brand")
        table.add_column("Case ID", no_wrap=True)
        table.add_column("Name")
        table.add_column("Investigator")
        table.add_column("Case Number")
        table.add_column("Status")
        table.add_column("Created At")

        for c in cases:
            table.add_row(
                c.id,
                c.name,
                c.investigator,
                c.case_number or "[dim]-[/dim]",
                c.status,
                c.created_at.isoformat(sep=" ", timespec="seconds"),
            )

        console.print(table)


@app.command("show")
def case_show(case_id: str = typer.Argument(..., help="Case ID to show")) -> None:
    """Show a single case and its evidence."""
    from backend.db.models import Case

    console = get_console()
    section_header(console, "Case Detail")

    with db_session() as db:
        case = db.get(Case, case_id)
        if case is None:
            error(console, f"Case not found: {case_id}")
            raise typer.Exit(code=ExitCode.NOT_FOUND)

        table = fact_table()
        table.add_row("[field]Case ID:[/field]", case.id)
        table.add_row("[field]Name:[/field]", case.name)
        table.add_row("[field]Investigator:[/field]", case.investigator)
        table.add_row("[field]Case Number:[/field]", case.case_number or "[dim]-[/dim]")
        table.add_row("[field]Description:[/field]", case.description or "[dim]-[/dim]")
        table.add_row("[field]Status:[/field]", case.status)
        table.add_row("[field]Created At:[/field]", case.created_at.isoformat(sep=" ", timespec="seconds"))
        console.print(Panel(table, border_style="brand", title="Case"))

        if case.evidence_items:
            ev_table = Table(border_style="brand.dim", header_style="brand", title="Evidence")
            ev_table.add_column("Evidence ID", no_wrap=True)
            ev_table.add_column("Filename")
            ev_table.add_column("Vendor")
            ev_table.add_column("Status")
            for ev in case.evidence_items:
                ev_table.add_row(ev.id, ev.original_filename, ev.vendor or "[dim]-[/dim]", ev.status.value)
            console.print(ev_table)
        else:
            console.print("[dim]No evidence registered for this case yet.[/dim]")
