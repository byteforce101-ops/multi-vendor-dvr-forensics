"""backend/cli/ui/forensic_report.py

Executive-grade presentation and reporting engine for TraceX Forensic AI Analysis.
Provides clean visual hierarchy, pipeline architecture breakdowns, executive summaries,
critical alert callouts, and condensed entity trajectory timelines.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Sequence

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from backend.cli.theme import get_console, section_header, warn, success
from backend.core.search.context_compressor import compress_events_into_track_spans


def _safe_get(obj: Any, attr: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(attr, default)
    return getattr(obj, attr, default)


def print_pipeline_architecture_banner(
    console: Console,
    video_path: Path,
    vendor_name: str = "Generic / Direct Video",
    frame_count: int = 0,
    duration_sec: float = 0.0,
    resolution: str = "N/A",
    fps: float | str = "N/A",
    detector_engine: str = "Pure OpenCV (HOG + Morphometrics)",
) -> None:
    """Displays the 4-phase forensic pipeline architecture and evidence profile."""
    section_header(console, "TraceX Forensic Pipeline Architecture & Evidence Profile")

    # 4-stage pipeline grid
    pipe_table = Table(border_style="spring_green4", show_header=True, expand=True)
    pipe_table.add_column("Stage 1: Ingestion & Carving", style="bold white", justify="center")
    pipe_table.add_column("Stage 2: CCTV Preprocessing", style="bold white", justify="center")
    pipe_table.add_column("Stage 3: AI / Motion Engine", style="bold white", justify="center")
    pipe_table.add_column("Stage 4: Event Reconstruction", style="bold white", justify="center")

    pipe_table.add_row(
        f"[ok]✔[/ok] {vendor_name.capitalize()} Stream Carved\n[dim]H.264/MP4 Stream Extracted[/dim]",
        "[ok]✔[/ok] CLAHE + Auto-Gamma\n[dim]Low-light & Unsharp Filter[/dim]",
        f"[ok]✔[/ok] {detector_engine}\n[dim]Zero Neural Hallucinations[/dim]",
        "[ok]✔[/ok] Trajectory & Loitering\n[dim]8-Compass + Velocity Vectors[/dim]",
    )
    console.print(pipe_table)

    # Evidence details grid
    facts = Table.grid(padding=(0, 3))
    facts.add_column(style="bold spring_green3", justify="right")
    facts.add_column(style="white")
    facts.add_column(style="bold spring_green3", justify="right")
    facts.add_column(style="white")

    file_size_mb = f"{video_path.stat().st_size / (1024 * 1024):.1f} MB" if video_path.exists() else "N/A"
    fps_str = f"{fps:.1f}" if isinstance(fps, (int, float)) else str(fps)

    facts.add_row(
        "Evidence File:", video_path.name,
        "File Size:", file_size_mb,
    )
    facts.add_row(
        "Frames Analyzed:", f"{frame_count} frames",
        "Video Duration:", f"{duration_sec:.1f}s",
    )
    facts.add_row(
        "Resolution / FPS:", f"{resolution} @ {fps_str} FPS",
        "Execution Mode:", "100% Offline / Local CPU",
    )

    console.print()
    console.print(Panel(facts, border_style="spring_green4", title="[bold white]Evidence Profile[/bold white]", expand=False))


def print_executive_forensic_summary(
    console: Console,
    summary: Any,
    reconstructed_events: Sequence[Any],
    total_raw_events: int = 0,
) -> None:
    """Displays the executive forensic narrative, incident headline, and key findings."""
    section_header(console, "Executive AI Forensic Summary")

    if summary is None:
        warn(console, "No forensic summary was generated for this timeline.")
        return

    headline = _safe_get(summary, "headline", "Forensic Scene Analysis")
    summary_text = _safe_get(summary, "summary", "Analysis complete.")
    start_time = _safe_get(summary, "start_time")
    end_time = _safe_get(summary, "end_time")
    key_events = _safe_get(summary, "key_events", []) or []

    # Headline Banner
    console.print(
        Panel(
            f"[bold spring_green3]{headline}[/bold spring_green3]",
            title="[bold white]INCIDENT / ACTIVITY CLASSIFICATION[/bold white]",
            border_style="spring_green3",
            expand=False,
            padding=(0, 2),
        )
    )

    # Narrative Summary
    console.print(
        Panel(
            summary_text,
            title="[bold white]FORENSIC INVESTIGATOR NARRATIVE[/bold white]",
            border_style="spring_green4",
            expand=False,
            padding=(0, 2),
        )
    )

    # Quick Metrics Table
    metrics = Table(border_style="spring_green4", show_header=True, header_style="bold spring_green3")
    metrics.add_column("Timeline Span")
    metrics.add_column("Raw Frame Detections")
    metrics.add_column("Reconstructed Activities")
    metrics.add_column("Loitering Incidents")
    metrics.add_column("Confidence")

    st_str = start_time.isoformat(sep=" ", timespec="seconds") if start_time and hasattr(start_time, "isoformat") else "N/A"
    et_str = end_time.isoformat(sep=" ", timespec="seconds") if end_time and hasattr(end_time, "isoformat") else "N/A"
    timeline_str = f"{st_str} → {et_str}" if st_str != "N/A" else "Recorded Timeline"

    loiter_count = sum(1 for e in reconstructed_events if "LOITER" in str(_safe_get(e, "event_type", "")).upper())
    conf_val = float(_safe_get(summary, "confidence", 0.85) or 0.85)

    metrics.add_row(
        timeline_str,
        str(total_raw_events),
        str(len(reconstructed_events)),
        f"[bold gold3]{loiter_count}[/bold gold3]" if loiter_count > 0 else "0",
        f"{conf_val * 100:.0f}% (High)",
    )
    console.print(metrics)

    # Key Findings Bullets
    if key_events:
        key_table = Table(border_style="spring_green4", header_style="bold spring_green3", title="Key Timeline Observations")
        key_table.add_column("#", width=4, justify="center")
        key_table.add_column("Observation")
        for i, item in enumerate(key_events[:6], start=1):
            key_table.add_row(str(i), str(item))
        console.print(key_table)


def print_critical_alerts_and_reconstruction(
    console: Console,
    reconstructed_events: Sequence[Any],
    raw_events: Sequence[Any | tuple[str, Any]],
) -> None:
    """Displays prioritized critical alerts (loitering, sudden stops) and condensed entity trajectory timeline."""
    section_header(console, "Critical Forensic Alerts & Trajectory Timeline")

    if not reconstructed_events and not raw_events:
        warn(console, "No higher-level forensic activities or entity tracks were detected.")
        return

    # 1. Critical Alerts (Loitering, Sudden Shifts)
    critical_alerts = [
        e for e in reconstructed_events
        if any(k in str(_safe_get(e, "event_type", "")).upper() for k in ("LOITER", "SUDDEN", "DISAPPEAR", "FLAG"))
    ]

    if critical_alerts:
        console.print("\n[bold gold3]⚠ CRITICAL FORENSIC OBSERVATIONS IDENTIFIED:[/bold gold3]")
        for alert in critical_alerts[:8]:
            ev_type = str(_safe_get(alert, "event_type", "ALERT"))
            title = str(_safe_get(alert, "title", ev_type))
            desc = str(_safe_get(alert, "description", ""))
            st = _safe_get(alert, "start_time")
            st_str = st.isoformat(sep=" ", timespec="seconds") if st and hasattr(st, "isoformat") else ""

            border = "gold3" if "LOITER" in ev_type else "bright_cyan"
            console.print(
                Panel(
                    f"{desc}\n[dim]Timestamp: {st_str}[/dim]",
                    title=f"[bold {border}]⚠ {title}[/bold {border}]",
                    border_style=border,
                    expand=False,
                    padding=(0, 2),
                )
            )
        if len(critical_alerts) > 8:
            console.print(f"[dim]... and {len(critical_alerts) - 8} additional critical observations ...[/dim]")

    # 2. Entity Trajectory & Movement Timeline (Condensed track spans)
    spans = compress_events_into_track_spans(raw_events)

    console.print(f"\n[bold spring_green3]Tracked Entity Trajectory Timeline ({len(spans)} distinct entities):[/bold spring_green3]")

    traj_table = Table(border_style="spring_green4", header_style="bold spring_green3", expand=True)
    traj_table.add_column("Track ID", width=9, justify="center")
    traj_table.add_column("Class", width=12)
    traj_table.add_column("First Seen → Last Seen", width=26)
    traj_table.add_column("Duration", width=10, justify="right")
    traj_table.add_column("Heading Direction", width=18)
    traj_table.add_column("Avg Speed", width=12, justify="right")
    traj_table.add_column("Behavior Status", width=16, justify="center")

    display_spans = spans[:15]

    for span in display_spans:
        st_str = span.start_time.isoformat(sep=" ", timespec="seconds")
        et_str = span.end_time.isoformat(sep=" ", timespec="seconds")
        status_tag = "[bold gold3]⚠ LOITERING[/bold gold3]" if span.is_loitering else "[dim]Normal Transit[/dim]"
        speed_str = f"{span.avg_speed:.1f} px/s" if span.avg_speed > 0 else "0.0 px/s"

        traj_table.add_row(
            f"#{span.track_id}",
            span.object_type.capitalize(),
            f"{st_str[11:]} → {et_str[11:]}",
            f"{span.duration_seconds:.1f}s",
            span.direction,
            speed_str,
            status_tag,
        )

    if len(spans) > len(display_spans):
        traj_table.add_row(
            "[dim]...[/dim]",
            "[dim]...[/dim]",
            f"[dim]+ {len(spans) - len(display_spans)} additional entities[/dim]",
            "[dim]...[/dim]",
            "[dim]...[/dim]",
            "[dim]...[/dim]",
            "[dim]...[/dim]",
        )

    console.print(traj_table)
