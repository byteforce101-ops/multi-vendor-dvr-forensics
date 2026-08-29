"""dvrforensics search CASE_ID "natural language query" """

from __future__ import annotations

import typer
from rich.table import Table

from backend.cli.common import db_session
from backend.cli.exit_codes import ExitCode
from backend.cli.theme import error, fact_table, get_console, section_header, success, warn

def search(
    case_id: str = typer.Argument(..., help="Case ID to search within"),
    query: str = typer.Argument(..., help='Natural-language query, e.g. "people at camera 2 after 9pm"'),
) -> None:
    """Interpret a natural-language query into a filter, then list matching events."""
    console = get_console()
    section_header(console, "Search")

    from backend.db.models import Case

    with db_session() as db:
        case = db.get(Case, case_id)
        if case is None:
            error(console, f"Case not found: {case_id}")
            raise typer.Exit(code=ExitCode.NOT_FOUND)

        try:
            from backend.core.search.service import SearchService
            from backend.db.repositories.events_repository import EventsRepository
        except ImportError as exc:
            error(console, f"Search requires the 'groq' package, which isn't installed: {exc}")
            console.print("[dim]Install it with: pip install groq[/dim]")
            raise typer.Exit(code=ExitCode.MISSING_DEPENDENCY)
        except Exception as exc:
            # e.g. the groq client raising at import time because GROQ_API_KEY isn't set
            error(console, f"Search is unavailable: {exc}")
            console.print("[dim]Natural-language search requires GROQ_API_KEY to be set in the environment.[/dim]")
            raise typer.Exit(code=ExitCode.MISSING_DEPENDENCY)

        with console.status("[brand]Interpreting query...[/brand]", spinner="dots"):
            try:
                outcome = SearchService(EventsRepository(db)).search(case_id=case_id, nl_query=query)
            except Exception as exc:
                error(console, f"Search failed: {exc}")
                raise typer.Exit(code=ExitCode.GENERAL_ERROR)

        filt = outcome["filter"]
        results = outcome["results"]

        table = fact_table()
        table.add_row("[field]Query:[/field]", query)
        table.add_row("[field]Event types:[/field]", ", ".join(filt.get("event_types") or []) or "[dim]any[/dim]")
        table.add_row("[field]Camera:[/field]", filt.get("camera_id") or "[dim]any[/dim]")
        table.add_row("[field]From:[/field]", filt.get("start_time") or "[dim]any[/dim]")
        table.add_row("[field]To:[/field]", filt.get("end_time") or "[dim]any[/dim]")
        table.add_row("[field]Min confidence:[/field]", str(filt.get("min_confidence")) if filt.get("min_confidence") is not None else "[dim]any[/dim]")
        console.print(table)
        console.print()

        if not results:
            warn(console, "No matching events.")
            return

        events_table = Table(border_style="brand.dim", header_style="brand", title=f"{len(results)} matching event(s)")
        events_table.add_column("Type")
        events_table.add_column("Camera")
        events_table.add_column("Start")
        events_table.add_column("End")
        events_table.add_column("Confidence")

        for ev in results:
            events_table.add_row(
                ev.event_type,
                ev.camera_id,
                ev.start_time.isoformat(sep=" ", timespec="seconds"),
                ev.end_time.isoformat(sep=" ", timespec="seconds"),
                f"{ev.confidence:.2f}" if ev.confidence is not None else "[dim]-[/dim]",
            )

        console.print(events_table)
        success(console, f"{len(results)} matching event(s).")
