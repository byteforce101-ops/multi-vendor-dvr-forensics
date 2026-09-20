import string
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

from backend.parsers.registry import ParserManager, SPLIT_OR_CONTAINER_EXTS
from backend.parsers.common.evidence_reader import RawImageReader

app = typer.Typer(
    help="Detect the DVR vendor and parser for an evidence file."
)

console = Console()


def _format_hex_dump(data: bytes, max_bytes: int = 512) -> str:
    slice_data = data[:max_bytes]
    lines = []
    for offset in range(0, len(slice_data), 16):
        chunk = slice_data[offset : offset + 16]
        hex_bytes_left = " ".join(f"{b:02x}" for b in chunk[:8])
        hex_bytes_right = " ".join(f"{b:02x}" for b in chunk[8:])
        hex_str = f"{hex_bytes_left:<23}  {hex_bytes_right:<23}".rstrip()
        ascii_str = "".join(chr(b) if 32 <= b <= 126 else "." for b in chunk)
        lines.append(f"{offset:08x}  {hex_str:<48}  |{ascii_str}|")
    return "\n".join(lines)


def _extract_ascii_strings(data: bytes, min_length: int = 6) -> list[tuple[int, str]]:
    strings: list[tuple[int, str]] = []
    current: list[int] = []
    start_offset = 0

    for idx, b in enumerate(data):
        if 32 <= b <= 126:
            if not current:
                start_offset = idx
            current.append(b)
        else:
            if len(current) >= min_length:
                s = bytes(current).decode("ascii", errors="replace")
                strings.append((start_offset, s))
            current = []

    if len(current) >= min_length:
        s = bytes(current).decode("ascii", errors="replace")
        strings.append((start_offset, s))

    return strings


def _get_console() -> Console:
    c = Console()
    if not c.is_terminal or c.width < 120:
        return Console(width=max(120, c.width if c.width else 120))
    return c


@app.callback(invoke_without_command=True)
def detect(
    ctx: typer.Context,
    evidence_path: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
        help="Path to the evidence file.",
    ),
    show_all: bool = typer.Option(
        False,
        "--all",
        "-a",
        help="Show evaluation results for all registered parsers, hex dump, and extracted strings.",
    ),
):
    if ctx.invoked_subcommand is not None:
        return

    cli_console = _get_console()

    cli_console.print(
        Panel.fit(
            "[bold cyan]DVR FORENSICS PLATFORM[/bold cyan]\n"
            "Evidence Detection",
            border_style="cyan",
        )
    )

    manager = ParserManager()

    try:
        parser, confidence, info, candidates = manager.detect_candidates(
            str(evidence_path), exhaustive=show_all
        )
    except Exception as exc:
        cli_console.print(f"[bold red]Detection failed:[/bold red] {exc}")
        raise typer.Exit(code=1)

    file_table = Table(show_header=False, box=None)
    file_table.add_column(style="bold cyan")
    file_table.add_column()

    file_table.add_row("File", evidence_path.name)
    file_table.add_row("Path", str(evidence_path))
    file_table.add_row(
        "Size",
        f"{evidence_path.stat().st_size:,} bytes",
    )

    cli_console.print(file_table)
    cli_console.print()

    ext = evidence_path.suffix.lower()
    is_e01_or_split = ext in SPLIT_OR_CONTAINER_EXTS or any(
        evidence_path.name.lower().endswith(s) for s in (".e01", ".ex01", ".001")
    )

    if show_all:
        # All candidate parsers table
        candidates_table = Table(
            title="Candidate Parser Evaluations",
            show_header=True,
            box=box.ROUNDED,
            expand=False,
        )
        candidates_table.add_column("Vendor", style="bold cyan", overflow="fold", no_wrap=False)
        candidates_table.add_column("Parser Class", overflow="fold", no_wrap=False)
        candidates_table.add_column("Version")
        candidates_table.add_column("Matched")
        candidates_table.add_column("Confidence", justify="right")
        candidates_table.add_column("Details", overflow="fold", no_wrap=False)

        for c in candidates:
            if c.get("skipped"):
                matched_str = "[dim]skipped[/dim]"
                conf_str = "-"
                details = f"[dim]{c['skipped']}[/dim]"
            else:
                matched_str = "[bold green]Yes[/bold green]" if c.get("matched") else "[dim]No[/dim]"
                conf_str = f"{c['confidence']:.1%}" if c.get("matched") and c.get("confidence") is not None else "-"
                details = ", ".join(f"{k}={v}" for k, v in c["info"].items()) if c.get("info") else "-"
            candidates_table.add_row(
                c["vendor"],
                c["parser"],
                c["version"],
                matched_str,
                conf_str,
                details,
            )

        cli_console.print(candidates_table)
        cli_console.print()

        # Read first 4MB through EvidenceReader
        try:
            with RawImageReader(str(evidence_path)) as reader:
                file_len = reader.get_size()
                head_512 = reader.read(0, min(512, file_len))
                head_4mb = reader.read(0, min(4 * 1024 * 1024, file_len))

                # Hex dump
                hex_dump_str = _format_hex_dump(head_512)
                cli_console.print(
                    Panel(
                        hex_dump_str,
                        title=f"Hex Dump (First {len(head_512)} Bytes via EvidenceReader)",
                        border_style="cyan",
                    )
                )
                cli_console.print()

                # ASCII Strings >= 6 chars
                ascii_strings = _extract_ascii_strings(head_4mb, min_length=6)
                strings_table = Table(
                    title=f"Printable ASCII Strings (6+ Chars in First {len(head_4mb):,} Bytes) — Found: {len(ascii_strings)}",
                    show_header=True,
                    box=box.ROUNDED,
                )
                strings_table.add_column("Offset", style="cyan")
                strings_table.add_column("Hex Offset", style="dim")
                strings_table.add_column("String Value", overflow="fold")

                displayed_strings = ascii_strings[:40]
                for offset, s in displayed_strings:
                    strings_table.add_row(f"{offset:,}", f"0x{offset:08X}", s)

                cli_console.print(strings_table)
                if len(ascii_strings) > 40:
                    cli_console.print(f"[dim]... and {len(ascii_strings) - 40} more strings truncated[/dim]")
                cli_console.print()
        except Exception as exc:
            cli_console.print(f"[yellow]Warning: Could not read through EvidenceReader: {exc}[/yellow]\n")

    if is_e01_or_split:
        cli_console.print(
            Panel(
                "[bold yellow]Notice:[/bold yellow] Input file extension indicates an E01 container or split image.\n"
                "Proprietary parsers (such as Hikvision) inspect raw disk sectors directly and may not match\n"
                "unless the evidence is first reassembled or decompressed to a raw disk image.",
                border_style="yellow",
            )
        )
        cli_console.print()

    if parser is None:
        cli_console.print(
            Panel(
                "[yellow]No supported parser detected for this evidence file.[/yellow]",
                title="Detection Result",
                border_style="yellow",
            )
        )
        from backend.cli.exit_codes import ExitCode
        raise typer.Exit(code=ExitCode.UNSUPPORTED_VENDOR)

    result_table = Table(
        title="Detection Result",
        show_header=True,
    )

    result_table.add_column("Property", style="bold cyan")
    result_table.add_column("Value")

    result_table.add_row("Vendor", parser.vendor_name)
    result_table.add_row("Parser", parser.__class__.__name__)
    result_table.add_row("Version", parser.parser_version)
    result_table.add_row("Confidence", f"{confidence:.1%}")

    cli_console.print(result_table)

    if info:
        metadata_table = Table(
            title="Detection Metadata",
            show_header=True,
        )

        metadata_table.add_column("Key", style="cyan")
        metadata_table.add_column("Value")

        for key, value in info.items():
            metadata_table.add_row(str(key), str(value))

        cli_console.print(metadata_table)

    cli_console.print(
        "\n[bold green]✓ Supported evidence format detected.[/bold green]"
    )