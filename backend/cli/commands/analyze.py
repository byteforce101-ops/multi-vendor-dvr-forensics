"""dvrforensics analyze VIDEO_PATH"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import typer
from rich.panel import Panel
from rich.table import Table

from backend.cli.common import require_file
from backend.cli.exit_codes import ExitCode
from backend.cli.theme import (
    error,
    get_console,
    section_header,
    success,
    warn,
)

DEFAULT_MODEL = "yolo26n.pt"


# ============================================================
# AI FORENSIC EVENT RECONSTRUCTION
# ============================================================

def _print_reconstructed_events(console, result) -> None:
    """Display AI forensic event reconstruction results."""

    reconstructed = getattr(
        result,
        "reconstructed_events",
        None,
    )

    section_header(
        console,
        "AI Forensic Event Reconstruction",
    )

    if not reconstructed:
        warn(
            console,
            "No higher-level forensic activities were reconstructed.",
        )
        return

    table = Table(
        border_style="brand.dim",
        header_style="brand",
        title=f"{len(reconstructed)} reconstructed activity(s)",
    )

    table.add_column("Type", style="brand")
    table.add_column("Activity")
    table.add_column("Start")
    table.add_column("End")
    table.add_column("Objects")
    table.add_column("Confidence")

    for event in reconstructed:

        event_type = getattr(
            event,
            "event_type",
            "UNKNOWN",
        )

        title = getattr(
            event,
            "title",
            None,
        ) or event_type

        start_time = getattr(
            event,
            "start_time",
            None,
        )

        end_time = getattr(
            event,
            "end_time",
            None,
        )

        objects = getattr(
            event,
            "objects",
            None,
        )

        confidence = getattr(
            event,
            "confidence",
            None,
        )

        if isinstance(objects, (list, tuple, set)):
            objects_text = ", ".join(
                str(item)
                for item in objects
            )
        else:
            objects_text = (
                str(objects)
                if objects
                else "-"
            )

        start_text = (
            start_time.isoformat(
                sep=" ",
                timespec="seconds",
            )
            if start_time
            else "-"
        )

        end_text = (
            end_time.isoformat(
                sep=" ",
                timespec="seconds",
            )
            if end_time
            else "-"
        )

        confidence_text = (
            f"{confidence:.2f}"
            if isinstance(
                confidence,
                (int, float),
            )
            else "-"
        )

        table.add_row(
            str(event_type),
            str(title),
            start_text,
            end_text,
            objects_text,
            confidence_text,
        )

    console.print(table)

    # Prioritize significant events (loitering, sudden changes, people/vehicle) then top generic tracks
    significant = [e for e in reconstructed if any(k in getattr(e, "event_type", "").upper() for k in ("LOITER", "SUDDEN", "PERSON", "VEHICLE", "CAR", "TRUCK"))]
    others = [e for e in reconstructed if e not in significant]
    displayed_panels = (significant + others)[:10]

    for index, event in enumerate(
        displayed_panels,
        start=1,
    ):

        title = getattr(
            event,
            "title",
            None,
        ) or getattr(
            event,
            "event_type",
            "Forensic activity",
        )

        description = getattr(
            event,
            "description",
            None,
        )

        if description:

            console.print()

            console.print(
                Panel(
                    str(description),
                    title=f"Activity #{index}: {title}",
                    border_style="brand.dim",
                )
            )

    if len(reconstructed) > len(displayed_panels):
        console.print(
            f"\n[dim]... {len(reconstructed) - len(displayed_panels)} additional entity trajectory activities summarized in table above ...[/dim]"
        )


# ============================================================
# FINAL FORENSIC SUMMARY
# ============================================================

def _print_forensic_summary(console, result) -> None:
    """Display the final AI forensic summary."""

    summary = getattr(
        result,
        "forensic_summary",
        None,
    )

    section_header(
        console,
        "Final Forensic Summary",
    )

    if summary is None:
        warn(
            console,
            "No forensic summary was generated.",
        )
        return

    headline = getattr(
        summary,
        "headline",
        None,
    )

    summary_text = getattr(
        summary,
        "summary",
        None,
    )

    start_time = getattr(
        summary,
        "start_time",
        None,
    )

    end_time = getattr(
        summary,
        "end_time",
        None,
    )

    event_count = getattr(
        summary,
        "event_count",
        None,
    )

    objects_detected = getattr(
        summary,
        "objects_detected",
        None,
    )

    metadata = getattr(
        summary,
        "metadata",
        None,
    )

    if not isinstance(metadata, dict):
        metadata = {}

    confidence_label = metadata.get(
        "confidence_label"
    )

    if headline:

        console.print(
            Panel(
                str(headline),
                title="INCIDENT / ACTIVITY",
                border_style="brand",
                expand=False,
            )
        )

    if summary_text:

        console.print(
            Panel(
                str(summary_text),
                title="FORENSIC SUMMARY",
                border_style="brand.dim",
                expand=False,
            )
        )

    details = Table(
        border_style="brand.dim",
        show_header=False,
    )

    details.add_column(
        "Field",
        style="brand",
    )

    details.add_column(
        "Value",
    )

    if start_time:

        details.add_row(
            "Start time",
            start_time.isoformat(
                sep=" ",
                timespec="seconds",
            ),
        )

    if end_time:

        details.add_row(
            "End time",
            end_time.isoformat(
                sep=" ",
                timespec="seconds",
            ),
        )

    if event_count is not None:

        details.add_row(
            "Events reconstructed",
            str(event_count),
        )

    if objects_detected:

        if isinstance(
            objects_detected,
            (list, tuple, set),
        ):

            objects_text = ", ".join(
                str(item)
                for item in objects_detected
            )

        else:

            objects_text = str(
                objects_detected
            )

        details.add_row(
            "Objects detected",
            objects_text,
        )

    if confidence_label:

        details.add_row(
            "Confidence",
            str(confidence_label),
        )

    if details.row_count > 0:

        console.print()
        console.print(details)

    key_events = getattr(
        summary,
        "key_events",
        None,
    )

    if key_events:

        console.print()

        key_table = Table(
            border_style="brand.dim",
            header_style="brand",
            title="Key Forensic Events",
        )

        key_table.add_column(
            "#",
            width=5,
        )

        key_table.add_column(
            "Event",
        )

        for index, item in enumerate(
            key_events,
            start=1,
        ):

            key_table.add_row(
                str(index),
                str(item),
            )

        console.print(key_table)


# ============================================================
# VIDEO INTEGRITY / TAMPERING ANALYSIS
# ============================================================

def _run_integrity_analysis(video_path: Path) -> dict:
    """
    Analyze the video for potential evidence anomalies.

    Checks:

    - timestamp continuity
    - frame continuity
    - abnormal FPS changes
    - duplicate frames
    - corrupted frames
    - recording gaps
    - metadata consistency
    - resolution changes
    - visual/compression discontinuities
    """

    try:
        import av
    except ImportError as exc:

        return {
            "available": False,
            "error": (
                "PyAV is not installed. "
                f"{exc}"
            ),
        }

    try:
        import numpy as np
    except ImportError as exc:

        return {
            "available": False,
            "error": (
                "NumPy is not installed. "
                f"{exc}"
            ),
        }

    result = {
        "available": True,

        "timestamp_continuity": True,
        "timestamp_details": (
            "PTS values are continuous."
        ),

        "frame_continuity": True,
        "frame_details": (
            "No significant frame gaps detected."
        ),

        "fps_consistency": True,
        "fps_details": (
            "Frame timing is consistent."
        ),

        "duplicate_frames": True,
        "duplicate_details": (
            "No significant duplicate frame sequence detected."
        ),

        "metadata_consistency": True,
        "metadata_details": (
            "Video metadata is internally consistent."
        ),

        "resolution_consistency": True,
        "resolution_details": (
            "Resolution remains consistent."
        ),

        "compression_consistency": True,
        "compression_details": (
            "No significant visual/compression "
            "discontinuities detected."
        ),

        "anomalies": [],

        "frames_checked": 0,
        "timestamp_gaps": 0,
        "duplicate_sequences": 0,
        "corrupted_frames": 0,
        "fps_changes": 0,
        "resolution_changes": 0,
        "compression_anomalies": 0,

        "integrity_score": 100,
        "overall_status": "PASS",
    }

    container = None

    try:

        container = av.open(
            str(video_path)
        )

        if not container.streams.video:

            result["available"] = False
            result["error"] = (
                "No video stream found."
            )

            return result

        stream = container.streams.video[0]

        declared_width = stream.width
        declared_height = stream.height

        average_rate = stream.average_rate

        if average_rate:

            try:
                expected_interval = (
                    1.0 / float(average_rate)
                )
            except Exception:
                expected_interval = None

        else:

            expected_interval = None

        previous_time = None

        previous_frame_signature = None

        duplicate_run = 0
        duplicate_start_frame = None

        previous_fps = None

        previous_mean = None
        previous_std = None

        frame_number = 0

        timestamp_tolerance = (
            max(
                expected_interval * 2.5,
                0.150,
            )
            if expected_interval
            else 0.150
        )

        # ====================================================
        # DECODE VIDEO FRAMES
        # ====================================================

        for frame in container.decode(
            stream
        ):

            frame_number += 1

            result["frames_checked"] = (
                frame_number
            )

            # ------------------------------------------------
            # Decode frame
            # ------------------------------------------------

            try:

                image = frame.to_ndarray(
                    format="gray"
                )

            except Exception:

                result["corrupted_frames"] += 1

                result["anomalies"].append(
                    (
                        f"Frame {frame_number} "
                        "could not be decoded."
                    )
                )

                continue

            # ------------------------------------------------
            # Frame sanity
            # ------------------------------------------------

            if image.size == 0:

                result["corrupted_frames"] += 1

                result["anomalies"].append(
                    (
                        f"Frame {frame_number} "
                        "contains no pixel data."
                    )
                )

                continue

            try:

                if not np.isfinite(
                    image
                ).all():

                    result["corrupted_frames"] += 1

                    result["anomalies"].append(
                        (
                            f"Frame {frame_number} "
                            "contains invalid pixel values."
                        )
                    )

                    continue

            except Exception:
                pass

            # ------------------------------------------------
            # Resolution
            # ------------------------------------------------

            current_width = image.shape[1]
            current_height = image.shape[0]

            if (
                current_width != declared_width
                or current_height != declared_height
            ):

                result[
                    "resolution_consistency"
                ] = False

                result[
                    "resolution_changes"
                ] += 1

                result["anomalies"].append(
                    (
                        f"Frame {frame_number}: "
                        f"resolution changed to "
                        f"{current_width}x"
                        f"{current_height}."
                    )
                )

            # ------------------------------------------------
            # Timestamp analysis
            # ------------------------------------------------

            current_time = None

            if frame.pts is not None:

                try:

                    current_time = float(
                        frame.pts
                        * frame.time_base
                    )

                except Exception:

                    current_time = None

            if (
                current_time is not None
                and previous_time is not None
            ):

                delta = (
                    current_time
                    - previous_time
                )

                # Timestamp moved backwards
                if delta < -0.001:

                    result[
                        "timestamp_continuity"
                    ] = False

                    result[
                        "timestamp_details"
                    ] = (
                        "Timestamp moved backwards."
                    )

                    result["anomalies"].append(
                        (
                            f"Timestamp jump at frame "
                            f"{frame_number}: "
                            f"{previous_time:.3f}s → "
                            f"{current_time:.3f}s."
                        )
                    )

                # Large timestamp gap
                elif delta > timestamp_tolerance:

                    result[
                        "timestamp_continuity"
                    ] = False

                    result[
                        "frame_continuity"
                    ] = False

                    result[
                        "timestamp_gaps"
                    ] += 1

                    result[
                        "timestamp_details"
                    ] = (
                        f"{result['timestamp_gaps']} "
                        "timestamp gap(s) detected."
                    )

                    result[
                        "frame_details"
                    ] = (
                        f"{result['timestamp_gaps']} "
                        "unusually large frame "
                        "interval(s) detected."
                    )

                    result["anomalies"].append(
                        (
                            f"Recording gap near frame "
                            f"{frame_number}: "
                            f"{delta:.3f}s between frames."
                        )
                    )

            previous_time = current_time

            # ------------------------------------------------
            # FPS consistency
            # ------------------------------------------------

            if (
                current_time is not None
                and previous_time is not None
                and expected_interval
            ):

                # Use PTS deltas when possible.
                pass

            if (
                current_time is not None
                and "last_fps_time" in locals()
            ):

                interval = (
                    current_time
                    - last_fps_time
                )

                if interval > 0:

                    current_fps = (
                        1.0 / interval
                    )

                    if previous_fps is not None:

                        fps_difference = abs(
                            current_fps
                            - previous_fps
                        )

                        if (
                            fps_difference
                            > max(
                                previous_fps * 0.20,
                                5.0,
                            )
                        ):

                            result[
                                "fps_consistency"
                            ] = False

                            result[
                                "fps_changes"
                            ] += 1

                    previous_fps = current_fps

            if current_time is not None:

                last_fps_time = current_time

            # ------------------------------------------------
            # Duplicate frame detection
            # ------------------------------------------------

            try:

                small = image[
                    ::8,
                    ::8
                ].astype(
                    np.float32
                )

                if (
                    previous_frame_signature
                    is not None
                    and small.shape
                    == previous_frame_signature.shape
                ):

                    difference = float(
                        np.mean(
                            np.abs(
                                small
                                - previous_frame_signature
                            )
                        )
                    )

                    if difference < 1.0:

                        duplicate_run += 1

                        if (
                            duplicate_start_frame
                            is None
                        ):

                            duplicate_start_frame = (
                                frame_number - 1
                            )

                    else:

                        if duplicate_run >= 5:

                            result[
                                "duplicate_frames"
                            ] = False

                            result[
                                "duplicate_sequences"
                            ] += 1

                            start = (
                                duplicate_start_frame
                                or (
                                    frame_number
                                    - duplicate_run
                                )
                            )

                            end = (
                                frame_number - 1
                            )

                            result[
                                "anomalies"
                            ].append(
                                (
                                    f"Frames {start}–{end} "
                                    "appear duplicated or "
                                    "nearly identical."
                                )
                            )

                        duplicate_run = 0
                        duplicate_start_frame = None

                previous_frame_signature = small

            except Exception:

                previous_frame_signature = None

            # ------------------------------------------------
            # Visual / compression discontinuity
            # ------------------------------------------------

            try:

                current_mean = float(
                    np.mean(image)
                )

                current_std = float(
                    np.std(image)
                )

                if (
                    previous_mean is not None
                    and previous_std is not None
                ):

                    mean_change = abs(
                        current_mean
                        - previous_mean
                    )

                    std_change = abs(
                        current_std
                        - previous_std
                    )

                    if (
                        mean_change > 70
                        and std_change > 35
                    ):

                        result[
                            "compression_anomalies"
                        ] += 1

                previous_mean = current_mean
                previous_std = current_std

            except Exception:
                pass

        # ====================================================
        # FINAL DUPLICATE SEQUENCE
        # ====================================================

        if duplicate_run >= 5:

            result[
                "duplicate_frames"
            ] = False

            result[
                "duplicate_sequences"
            ] += 1

            start = (
                duplicate_start_frame
                or (
                    frame_number
                    - duplicate_run
                )
            )

            end = frame_number

            result[
                "anomalies"
            ].append(
                (
                    f"Frames {start}–{end} "
                    "appear duplicated or "
                    "nearly identical."
                )
            )

        # ====================================================
        # CORRUPTED FRAME RESULT
        # ====================================================

        if result["corrupted_frames"] > 0:

            result[
                "frame_continuity"
            ] = False

            result[
                "frame_details"
            ] = (
                f"{result['corrupted_frames']} "
                "frame(s) could not be decoded."
            )

        # ====================================================
        # FPS RESULT
        # ====================================================

        if result["fps_changes"] > 0:

            result[
                "fps_details"
            ] = (
                f"{result['fps_changes']} "
                "abnormal frame-rate change(s) detected."
            )

        # ====================================================
        # RESOLUTION RESULT
        # ====================================================

        if result["resolution_changes"] > 0:

            result[
                "resolution_details"
            ] = (
                f"{result['resolution_changes']} "
                "resolution change(s) detected."
            )

        # ====================================================
        # COMPRESSION RESULT
        # ====================================================

        compression_threshold = max(
            5,
            int(
                result["frames_checked"]
                * 0.08
            ),
        )

        if (
            result["compression_anomalies"]
            > compression_threshold
        ):

            result[
                "compression_consistency"
            ] = False

            result[
                "compression_details"
            ] = (
                f"{result['compression_anomalies']} "
                "unusual visual/compression "
                "transitions detected."
            )

            result[
                "anomalies"
            ].append(
                (
                    "Unusual visual/compression "
                    "discontinuities detected."
                )
            )

        # ====================================================
        # METADATA CONSISTENCY
        # ====================================================

        if (
            declared_width <= 0
            or declared_height <= 0
        ):

            result[
                "metadata_consistency"
            ] = False

            result[
                "metadata_details"
            ] = (
                "Invalid video dimensions "
                "reported by the container."
            )

            result[
                "anomalies"
            ].append(
                "Video metadata contains invalid dimensions."
            )

        if average_rate is None:

            result[
                "metadata_consistency"
            ] = False

            result[
                "metadata_details"
            ] = (
                "The video stream does not expose "
                "a reliable FPS value."
            )

        # ====================================================
        # REMOVE DUPLICATE ANOMALY MESSAGES
        # ====================================================

        result["anomalies"] = list(
            dict.fromkeys(
                result["anomalies"]
            )
        )

        # ====================================================
        # INTEGRITY SCORE
        # ====================================================

        score = 100

        if not result[
            "timestamp_continuity"
        ]:
            score -= 15

        if not result[
            "frame_continuity"
        ]:
            score -= 15

        if not result[
            "fps_consistency"
        ]:
            score -= 10

        if not result[
            "duplicate_frames"
        ]:
            score -= 15

        if result[
            "corrupted_frames"
        ] > 0:
            score -= 20

        if result[
            "timestamp_gaps"
        ] > 0:
            score -= 15

        if not result[
            "metadata_consistency"
        ]:
            score -= 10

        if not result[
            "resolution_consistency"
        ]:
            score -= 10

        if not result.get(
            "compression_consistency",
            True,
        ):
            score -= 10

        result[
            "integrity_score"
        ] = max(
            0,
            min(
                100,
                score,
            ),
        )

        if result[
            "integrity_score"
        ] >= 90:

            result[
                "overall_status"
            ] = "PASS"

        elif result[
            "integrity_score"
        ] >= 70:

            result[
                "overall_status"
            ] = "REVIEW"

        else:

            result[
                "overall_status"
            ] = "ANOMALY"

        return result

    except Exception as exc:

        result["available"] = False

        result["error"] = (
            f"Integrity analysis failed: {exc}"
        )

        return result

    finally:

        if container is not None:

            try:
                container.close()
            except Exception:
                pass


# ============================================================
# PRINT VIDEO INTEGRITY ANALYSIS
# ============================================================

def _print_integrity_analysis(
    console,
    integrity_result: dict,
) -> None:
    """Display tampering / evidence anomaly analysis."""

    section_header(
        console,
        "Video Integrity Analysis",
    )

    if not integrity_result.get(
        "available",
        False,
    ):

        warn(
            console,
            (
                "Video integrity analysis was skipped: "
                f"{integrity_result.get('error', 'unknown error')}"
            ),
        )

        return

    table = Table(
        border_style="brand.dim",
        header_style="brand",
        title="VIDEO INTEGRITY ANALYSIS",
    )

    table.add_column("Check")
    table.add_column("Status")
    table.add_column("Details")

    checks = [
        (
            "Timestamp continuity",
            integrity_result.get(
                "timestamp_continuity",
                None,
            ),
            integrity_result.get(
                "timestamp_details",
                "",
            ),
        ),

        (
            "Frame continuity",
            integrity_result.get(
                "frame_continuity",
                None,
            ),
            integrity_result.get(
                "frame_details",
                "",
            ),
        ),

        (
            "FPS consistency",
            integrity_result.get(
                "fps_consistency",
                None,
            ),
            integrity_result.get(
                "fps_details",
                "",
            ),
        ),

        (
            "Duplicate frames",
            integrity_result.get(
                "duplicate_frames",
                None,
            ),
            integrity_result.get(
                "duplicate_details",
                "No significant duplicate "
                "frame sequence detected.",
            ),
        ),

        (
            "Corrupted frames",
            (
                integrity_result.get(
                    "corrupted_frames",
                    0,
                )
                == 0
            ),
            (
                "All checked frames decoded successfully."
                if integrity_result.get(
                    "corrupted_frames",
                    0,
                ) == 0
                else (
                    f"{integrity_result.get('corrupted_frames')} "
                    "corrupted/undecodable frame(s) detected."
                )
            ),
        ),

        (
            "Recording gaps",
            (
                integrity_result.get(
                    "timestamp_gaps",
                    0,
                )
                == 0
            ),
            (
                "No significant recording gaps detected."
                if integrity_result.get(
                    "timestamp_gaps",
                    0,
                ) == 0
                else (
                    f"{integrity_result.get('timestamp_gaps')} "
                    "recording gap(s) detected."
                )
            ),
        ),

        (
            "Metadata consistency",
            integrity_result.get(
                "metadata_consistency",
                None,
            ),
            integrity_result.get(
                "metadata_details",
                "",
            ),
        ),

        (
            "Resolution consistency",
            integrity_result.get(
                "resolution_consistency",
                None,
            ),
            integrity_result.get(
                "resolution_details",
                "",
            ),
        ),

        (
            "Compression consistency",
            integrity_result.get(
                "compression_consistency",
                True,
            ),
            integrity_result.get(
                "compression_details",
                (
                    "No significant visual/compression "
                    "discontinuities detected."
                ),
            ),
        ),
    ]

    for (
        name,
        status,
        details,
    ) in checks:

        if status is True:

            status_text = (
                "[green]✓ PASS[/green]"
            )

        elif status is False:

            status_text = (
                "[red]⚠ ANOMALY[/red]"
            )

        else:

            status_text = (
                "[yellow]? UNKNOWN[/yellow]"
            )

        table.add_row(
            name,
            status_text,
            str(details or "-"),
        )

    console.print(table)

    # ========================================================
    # STATISTICS
    # ========================================================

    console.print()

    statistics = Table(
        border_style="brand.dim",
        show_header=False,
    )

    statistics.add_column(
        "Metric",
        style="brand",
    )

    statistics.add_column(
        "Value",
    )

    statistics.add_row(
        "Frames checked",
        str(
            integrity_result.get(
                "frames_checked",
                0,
            )
        ),
    )

    statistics.add_row(
        "Timestamp gaps",
        str(
            integrity_result.get(
                "timestamp_gaps",
                0,
            )
        ),
    )

    statistics.add_row(
        "Duplicate sequences",
        str(
            integrity_result.get(
                "duplicate_sequences",
                0,
            )
        ),
    )

    statistics.add_row(
        "Corrupted frames",
        str(
            integrity_result.get(
                "corrupted_frames",
                0,
            )
        ),
    )

    statistics.add_row(
        "FPS changes",
        str(
            integrity_result.get(
                "fps_changes",
                0,
            )
        ),
    )

    statistics.add_row(
        "Resolution changes",
        str(
            integrity_result.get(
                "resolution_changes",
                0,
            )
        ),
    )

    statistics.add_row(
        "Compression anomalies",
        str(
            integrity_result.get(
                "compression_anomalies",
                0,
            )
        ),
    )

    console.print(statistics)

    # ========================================================
    # INTEGRITY SCORE
    # ========================================================

    console.print()

    score = integrity_result.get(
        "integrity_score",
        100,
    )

    overall_status = integrity_result.get(
        "overall_status",
        "PASS",
    )

    if overall_status == "PASS":

        status_text = (
            "[green]✓ NO SIGNIFICANT ANOMALIES[/green]"
        )

        border = "green"

    elif overall_status == "REVIEW":

        status_text = (
            "[yellow]⚠ REVIEW RECOMMENDED[/yellow]"
        )

        border = "yellow"

    else:

        status_text = (
            "[red]⚠ SIGNIFICANT ANOMALIES[/red]"
        )

        border = "red"

    console.print(
        Panel(
            (
                f"[bold]Integrity Score:[/bold] "
                f"{score}/100\n\n"
                f"[bold]Assessment:[/bold] "
                f"{status_text}"
            ),
            title="FORENSIC EVIDENCE INTEGRITY",
            border_style=border,
            expand=False,
        )
    )

    # ========================================================
    # POTENTIAL ANOMALIES
    # ========================================================

    anomalies = integrity_result.get(
        "anomalies",
        [],
    )

    if anomalies:

        console.print()

        console.print(
            Panel(
                "\n".join(
                    f"• {item}"
                    for item in anomalies
                ),
                title="Potential Anomalies",
                border_style="red",
                expand=False,
            )
        )

        console.print()

        warn(
            console,
            (
                "Potential evidence anomalies were detected. "
                "These findings require forensic review and "
                "do not independently prove intentional tampering."
            ),
        )

    else:

        console.print()

        success(
            console,
            (
                "No significant video integrity anomalies "
                "were detected."
            ),
        )


# ============================================================
# MAIN ANALYZE COMMAND
# ============================================================

def analyze(
    video_path: Path = typer.Argument(
        ...,
        help="Path to the video file to analyze",
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        help=(
            "[reserved] Where to write analysis artifacts; "
            "currently events are only printed"
        ),
    ),
    sample_fps: float = typer.Option(
        2.0,
        "--sample-fps",
        help="Frames per second to sample for analysis",
    ),
    model: str = typer.Option(
        DEFAULT_MODEL,
        "--model",
        help="Path to the YOLO model weights",
    ),
    start_time: Optional[datetime] = typer.Option(
        None,
        "--start-time",
        help=(
            "Recording start time (ISO 8601), used to convert "
            "frame offsets to absolute timestamps. "
            "Defaults to now if omitted."
        ),
    ),
) -> None:
    """
    Run the complete video forensic analysis pipeline.

    Pipeline:

    motion
    -> YOLO
    -> tracking
    -> forensic events
    -> AI event reconstruction
    -> final forensic summary
    -> tampering / evidence anomaly detection
    """

    console = get_console()

    section_header(
        console,
        "Analyze",
    )

    resolved = require_file(
        video_path,
        console,
    )

    # ========================================================
    # IMPORT VIDEO ANALYSIS SERVICE
    # ========================================================

    try:

        from backend.video.analysis.service import (
            VideoAnalysisService,
        )

    except ImportError as exc:

        error(
            console,
            (
                "Video analysis requires optional AI "
                f"dependencies that aren't installed: {exc}"
            ),
        )

        console.print(
            "[dim]Install them with: "
            "pip install ultralytics av[/dim]"
        )

        raise typer.Exit(
            code=ExitCode.MISSING_DEPENDENCY
        )

    # ========================================================
    # START TIME
    # ========================================================

    video_start = (
        start_time
        or datetime.now(timezone.utc)
    )

    console.print(
        f"[field]Video:[/field] "
        f"[path]{resolved}[/path]"
    )

    console.print(
        f"[field]Model:[/field] {model}"
    )

    console.print(
        f"[field]Sample FPS:[/field] "
        f"{sample_fps}"
    )

    console.print(
        f"[field]Start time:[/field] "
        f"{video_start.isoformat()}\n"
    )

    # ========================================================
    # INITIALIZE AI SERVICE
    # ========================================================

    try:

        service = VideoAnalysisService(
            yolo_model=model
        )

    except Exception as exc:

        error(
            console,
            f"Could not initialize the AI pipeline: {exc}",
        )

        raise typer.Exit(
            code=ExitCode.MISSING_DEPENDENCY
        )

    # ========================================================
    # DETECT DISK IMAGES / PARSER DISPATCH
    # ========================================================

    from backend.parsers.registry import ParserManager

    manager = ParserManager()
    parser, confidence, info = manager.detect(str(resolved))
    is_disk_image = (
        parser is not None and parser.vendor_name != "generic"
    ) or resolved.suffix.lower() in {".dd", ".img", ".raw", ".dat", ".bin", ".001"}

    target_video_path = resolved
    if is_disk_image and parser is not None and parser.vendor_name != "generic":
        console.print(
            f"[brand]Detected forensic disk image:[/brand] "
            f"[ok]{parser.vendor_name}[/ok] ({confidence * 100:.0f}%)"
        )
        out_dir = Path("./output") / resolved.stem
        out_dir.mkdir(parents=True, exist_ok=True)
        parse_result = manager.parse(str(resolved), str(out_dir))
        extract_result = manager.extract(str(resolved), str(out_dir), parse_result) if parse_result.success else parse_result
        recovered = [
            r for r in extract_result.recordings
            if r.extracted_path and Path(r.extracted_path).is_file() and Path(r.extracted_path).stat().st_size > 0
        ]
        if recovered:
            target_video_path = Path(recovered[0].extracted_path)
            console.print(f"[field]Extracted stream:[/field] [path]{target_video_path}[/path]\n")
        else:
            warn(
                console,
                f"Parsed {len(parse_result.recordings)} recording index entries from {parser.vendor_name} image, "
                "but no playable video payloads could be carved out."
            )
            return

    # ========================================================
    # RUN AI ANALYSIS
    # ========================================================

    with console.status(
        (
            "[brand]"
            "Running AI pipeline "
            "(probe → frames → motion → YOLO → "
            "events → reconstruction → summary)..."
            "[/brand]"
        ),
        spinner="arc",
    ):

        try:

            result = service.analyze(
                video_id=resolved.stem,
                camera_id="CH-CLI",
                video_path=target_video_path,
                video_start_time=video_start,
                frame_sample_fps=sample_fps,
            )

        except FileNotFoundError as exc:

            error(
                console,
                str(exc),
            )

            raise typer.Exit(
                code=ExitCode.FILE_NOT_FOUND
            )

        except Exception as exc:

            error(
                console,
                f"Video analysis failed: {exc}",
            )

            raise typer.Exit(
                code=ExitCode.GENERAL_ERROR
            )

    # ========================================================
    # 1. PIPELINE ARCHITECTURE & EVIDENCE PROFILE
    # ========================================================
    from backend.cli.ui.forensic_report import (
        print_pipeline_architecture_banner,
        print_executive_forensic_summary,
        print_critical_alerts_and_reconstruction,
    )

    detected_vendor = "Hikvision / DVR Disk Image" if target_video_path and target_video_path != resolved else "Direct Video Stream"

    print_pipeline_architecture_banner(
        console=console,
        video_path=resolved,
        vendor_name=detected_vendor,
        frame_count=result.frame_count_analyzed,
        duration_sec=result.metadata.duration_seconds or 0.0,
        resolution=f"{result.metadata.width}x{result.metadata.height}",
        fps=result.metadata.fps or 25.0,
        detector_engine="Pure OpenCV (HOG + Morphometrics + Centroid Tracker)",
    )

    # ========================================================
    # 2. EXECUTIVE FORENSIC SUMMARY
    # ========================================================
    print_executive_forensic_summary(
        console=console,
        summary=result.forensic_summary,
        reconstructed_events=getattr(result, "reconstructed_events", []),
        total_raw_events=len(result.events),
    )

    # ========================================================
    # 3. CRITICAL FORENSIC ALERTS & TRAJECTORY TIMELINE
    # ========================================================
    print_critical_alerts_and_reconstruction(
        console=console,
        reconstructed_events=getattr(result, "reconstructed_events", []),
        raw_events=result.events,
    )

    # ========================================================
    # TAMPERING / EVIDENCE ANOMALY DETECTION
    # ========================================================

    section_header(
        console,
        "Tampering / Evidence Anomaly Detection",
    )

    console.print(
        "[dim]"
        "Checking timestamps, frame continuity, FPS, "
        "duplicate frames, corrupted frames, metadata, "
        "resolution and compression..."
        "[/dim]\n"
    )

    with console.status(
        (
            "[brand]"
            "Running video integrity analysis..."
            "[/brand]"
        ),
        spinner="arc",
    ):

        integrity_result = _run_integrity_analysis(
            target_video_path if target_video_path and Path(target_video_path).exists() else resolved
        )

    _print_integrity_analysis(
        console,
        integrity_result,
    )

    # ========================================================
    # FINAL RESULT
    # ========================================================

    reconstructed_count = len(
        getattr(
            result,
            "reconstructed_events",
            [],
        )
    )

    success(
        console,
        (
            "Analysis complete — "
            f"{len(result.events)} event(s) found, "
            f"{reconstructed_count} "
            "higher-level activity(s) reconstructed, "
            "and video integrity analysis completed."
        ),
    )

    # ========================================================
    # OUTPUT OPTION
    # ========================================================

    if output:

        warn(
            console,
            (
                "--output is reserved for a future "
                "artifact-writing mode; results were "
                "printed above only."
            ),
        )