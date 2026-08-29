from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from backend.db.database import SessionLocal
from backend.db.models import Case

app = typer.Typer(
    help="Case management commands.",
    no_args_is_help=True,
)

console = Console()


@app.command("create")
def create_case(
    name: str = typer.Argument(
        ...,
        help="Name of the investigation.",
    ),
    investigator: str = typer.Option(
        ...,
        "--investigator",
        "-i",
        help="Name of the investigator.",
    ),
    case_number: Optional[str] = typer.Option(
        None,
        "--case-number",
        help="Optional case number.",
    ),
    description: Optional[str] = typer.Option(
        None,
        "--description",
        "-d",
        help="Optional case description.",
    ),
):
    console.print(
        Panel.fit(
            "[bold cyan]DVR FORENSICS PLATFORM[/bold cyan]\n"
            "Case Creation",
            border_style="cyan",
        )
    )

    db = SessionLocal()

    try:
        if case_number:
            existing_case = (
                db.query(Case)
                .filter(Case.case_number == case_number)
                .one_or_none()
            )

            if existing_case is not None:
                console.print(
                    f"[bold red]A case with number "
                    f"'{case_number}' already exists.[/bold red]"
                )
                raise typer.Exit(code=1)

        case = Case(
            name=name,
            investigator=investigator,
            case_number=case_number,
            description=description,
        )

        db.add(case)
        db.commit()
        db.refresh(case)

        table = Table(title="Case Created Successfully")

        table.add_column("Property", style="bold cyan")
        table.add_column("Value")

        table.add_row("Case ID", case.id)
        table.add_row("Name", case.name)
        table.add_row("Investigator", case.investigator)

        table.add_row(
            "Case Number",
            case.case_number or "Not provided",
        )

        table.add_row(
            "Description",
            case.description or "Not provided",
        )

        table.add_row("Status", case.status)

        table.add_row(
            "Created",
            str(case.created_at),
        )

        console.print()
        console.print(table)

        console.print(
            "\n[bold green]✓ Case created successfully.[/bold green]"
        )

    except typer.Exit:
        raise

    except Exception as exc:
        db.rollback()

        console.print(
            f"\n[bold red]Failed to create case:[/bold red] {exc}"
        )

        raise typer.Exit(code=1)

    finally:
        db.close()


@app.command("list")
def list_cases():
    db = SessionLocal()

    try:
        cases = (
            db.query(Case)
            .order_by(Case.created_at.desc())
            .all()
        )

        if not cases:
            console.print("[yellow]No cases found.[/yellow]")
            return

        table = Table(title="Cases")

        table.add_column("Case ID", style="cyan")
        table.add_column("Name")
        table.add_column("Case Number")
        table.add_column("Investigator")
        table.add_column("Status")
        table.add_column("Created")

        for case in cases:
            table.add_row(
                case.id,
                case.name,
                case.case_number or "-",
                case.investigator,
                case.status,
                str(case.created_at),
            )

        console.print(table)

    finally:
        db.close()


@app.command("show")
def show_case(
    case_id: str = typer.Argument(
        ...,
        help="ID of the case.",
    ),
):
    db = SessionLocal()

    try:
        case = (
            db.query(Case)
            .filter(Case.id == case_id)
            .one_or_none()
        )

        if case is None:
            console.print(
                "[bold red]Case not found.[/bold red]"
            )
            raise typer.Exit(code=1)

        table = Table(title="Case Details")

        table.add_column("Property", style="bold cyan")
        table.add_column("Value")

        table.add_row("Case ID", case.id)
        table.add_row("Name", case.name)
        table.add_row("Investigator", case.investigator)

        table.add_row(
            "Case Number",
            case.case_number or "Not provided",
        )

        table.add_row(
            "Description",
            case.description or "Not provided",
        )

        table.add_row("Status", case.status)

        table.add_row(
            "Created",
            str(case.created_at),
        )

        table.add_row(
            "Evidence Items",
            str(len(case.evidence_items)),
        )

        console.print(table)

    finally:
        db.close()