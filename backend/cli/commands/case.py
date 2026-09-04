from typing import Optional

import typer
from rich.table import Table

from backend.cli.common import db_session
from backend.cli.exit_codes import ExitCode
from backend.cli.theme import get_console, section_header, success, error, warn
from backend.db.models import Case

app = typer.Typer(
    help="Case management commands.",
    no_args_is_help=True,
)

console = get_console()


@app.command("create")
def create_case(
    name: Optional[str] = typer.Option(
        None,
        "--name",
        "-n",
        help="Name of the investigation.",
    ),
    name_arg: Optional[str] = typer.Argument(
        None,
        help="Name of the investigation (positional).",
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
    case_name = name or name_arg
    if not case_name:
        error(console, "Case name is required.")
        raise typer.Exit(code=ExitCode.INVALID_ARGUMENT)

    with db_session() as db:
        if case_number:
            existing_case = (
                db.query(Case)
                .filter(Case.case_number == case_number)
                .one_or_none()
            )

            if existing_case is not None:
                error(console, f"A case with number '{case_number}' already exists.")
                raise typer.Exit(code=ExitCode.GENERAL_ERROR)

        case = Case(
            name=case_name,
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
        table.add_row("Case Number", case.case_number or "Not provided")
        table.add_row("Description", case.description or "Not provided")
        table.add_row("Status", case.status)
        table.add_row("Created", str(case.created_at))

        console.print()
        console.print(table)
        success(console, "Created case successfully.")


@app.command("list")
def list_cases():
    with db_session() as db:
        cases = (
            db.query(Case)
            .order_by(Case.created_at.desc())
            .all()
        )

        if not cases:
            warn(console, "No cases found.")
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


@app.command("show")
def show_case(
    case_id: str = typer.Argument(
        ...,
        help="ID of the case.",
    ),
):
    with db_session() as db:
        case = (
            db.query(Case)
            .filter(Case.id == case_id)
            .one_or_none()
        )

        if case is None:
            error(console, "Case not found.")
            raise typer.Exit(code=ExitCode.NOT_FOUND)

        table = Table(title="Case Details")
        table.add_column("Property", style="bold cyan")
        table.add_column("Value")

        table.add_row("Case ID", case.id)
        table.add_row("Name", case.name)
        table.add_row("Investigator", case.investigator)
        table.add_row("Case Number", case.case_number or "Not provided")
        table.add_row("Description", case.description or "Not provided")
        table.add_row("Status", case.status)
        table.add_row("Created", str(case.created_at))
        table.add_row("Evidence Items", str(len(case.evidence_items)))

        console.print(table)