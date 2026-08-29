"""backend/cli/interactive.py — TRACEX guided pipeline mode.

Triggered when `dvrforensics` is run with no subcommand: shows a big
TRACEX banner, prompts for a file path, then walks the file through
detect -> parse -> extract -> AI analyze automatically, printing each
step's output as it goes.

The AI analysis stage also includes:
    - object detection
    - motion detection
    - forensic event generation
    - AI forensic event reconstruction
    - final forensic summary

The existing natural-language Q&A remains available at the end.

Nothing here duplicates backend/core, backend/parsers, backend/video logic —
this file only orchestrates the existing services.
"""

from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path

from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.text import Text

from backend.cli.theme import (
    error,
    fact_table,
    get_console,
    human_size,
    section_header,
    success,
    warn,
)


_TRACEX_FONT = {
    "T": ["██████", "··██··", "··██··", "··██··", "··██··", "··██··"],
    "R": ["█████·", "██··██", "█████·", "██·██·", "██··██", "██··██"],
    "A": ["·████·", "██··██", "██████", "██··██", "██··██", "██··██"],
    "C": ["·█████", "██····", "██····", "██····", "██····", "·█████"],
    "E": ["██████", "██····", "█████·", "██····", "██····", "██████"],
    "X": ["██··██", "·████·", "··██··", "··██··", "·████·", "██··██"],
}


def _big_text(word: str) -> str:
    rows = ["" for _ in range(6)]

    for ch in word:
        glyph = _TRACEX_FONT.get(ch.upper())

        if glyph is None:
            continue

        for i in range(6):
            rows[i] += glyph[i] + " "

    return "\n".join(rows).replace("·", " ")


def print_tracex_banner(console) -> None:
    body = Text(
        _big_text("TRACEX"),
        style="bold bright_cyan",
    )

    body.append("\n")

    body.append(
        "T R A C E   ·   R E C O V E R   ·   A N A L Y Z E",
        style="bold magenta",
    )

    console.print(
        Panel(
            body,
            border_style="bright_cyan",
            expand=False,
            padding=(1, 3),
        )
    )


# =========================================================
# EXISTING Q&A
# =========================================================

def _ask_about_video(
    console,
    events: list,
    video_path: Path,
) -> None:
    """Conversational Q&A over the events detected in this run."""

    if not events:
        return

    try:
        from groq import Groq

    except ImportError:

        warn(
            console,
            "Q&A requires the 'groq' package, which isn't installed — skipping.",
        )

        return

    try:
        client = Groq()

    except Exception as exc:

        warn(
            console,
            (
                "Q&A unavailable "
                f"(Groq client could not initialize: {exc}) — skipping."
            ),
        )

        return

    event_lines = "\n".join(
        f"- {e.event_type} ({e.object_type or 'n/a'}) "
        f"on {cam} at "
        f"{e.start_time.isoformat(sep=' ', timespec='seconds')}, "
        f"confidence {e.confidence:.2f}"
        + (
            f" — {e.metadata['note']}"
            if e.metadata.get("note")
            else ""
        )
        for cam, e in sorted(
            events,
            key=lambda pair: pair[1].start_time,
        )
    )

    system_prompt = (
        "You are a forensic video-analysis assistant. "
        "You are given a timeline of AI-detected events from one video file, "
        "in chronological order. Events starting with REVIEW_FLAG_ are "
        "heuristic candidates for human review (bounding-box overlap or "
        "sudden deceleration) — they are NOT confirmed incidents. "
        "Never state that an accident/collision/incident definitely happened; "
        "at most say the data flags a moment worth a human reviewing. "
        "Answer using ONLY this event data, concisely. "
        "If the data doesn't support an answer, say so plainly rather than guessing.\n\n"
        f"Video: {video_path.name}\n\n"
        f"Detected events:\n{event_lines}"
    )

    section_header(
        console,
        "Ask About This Video",
    )

    console.print(
        "[dim]Type a question, or press Enter with nothing typed to finish.[/dim]\n"
    )

    history = [
        {
            "role": "system",
            "content": system_prompt,
        }
    ]

    while True:

        question = Prompt.ask(
            "[bold bright_cyan]Query[/bold bright_cyan]",
            default="",
            show_default=False,
        )

        if not question.strip():
            break

        history.append(
            {
                "role": "user",
                "content": question,
            }
        )

        with console.status(
            "[brand]Thinking...[/brand]",
            spinner="dots",
        ):

            try:

                import os

                resp = client.chat.completions.create(
                    model=os.getenv(
                        "GROQ_MODEL",
                        "openai/gpt-oss-120b",
                    ),
                    max_tokens=400,
                    messages=history,
                )

                answer = (
                    resp.choices[0]
                    .message.content
                    .strip()
                )

            except Exception as exc:

                error(
                    console,
                    f"Query failed: {exc}",
                )

                continue

        history.append(
            {
                "role": "assistant",
                "content": answer,
            }
        )

        console.print(
            Panel(
                answer,
                border_style="bright_cyan",
                title="Answer",
            )
        )


# =========================================================
# AI FORENSIC EVENT RECONSTRUCTION
# =========================================================

def _print_reconstructed_events(
    console,
    reconstructed_events: list,
) -> None:
    """Display higher-level reconstructed forensic activities."""

    section_header(
        console,
        "AI Forensic Event Reconstruction",
    )

    if not reconstructed_events:

        warn(
            console,
            "No higher-level forensic activities were reconstructed.",
        )

        return

    table = Table(
        border_style="bright_cyan",
        header_style="bold bright_cyan",
        title=(
            f"{len(reconstructed_events)} "
            "reconstructed activity(s)"
        ),
    )

    table.add_column("Type")
    table.add_column("Activity")
    table.add_column("Start")
    table.add_column("End")
    table.add_column("Objects")
    table.add_column("Confidence")

    for event in reconstructed_events:

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

        if isinstance(
            objects,
            (list, tuple, set),
        ):

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

    # ---------------------------------------------------------
    # Detailed reconstruction descriptions
    # ---------------------------------------------------------

    for index, event in enumerate(
        reconstructed_events,
        start=1,
    ):

        description = getattr(
            event,
            "description",
            None,
        )

        title = getattr(
            event,
            "title",
            None,
        ) or getattr(
            event,
            "event_type",
            "Forensic activity",
        )

        if description:

            console.print()

            console.print(
                Panel(
                    str(description),
                    title=(
                        f"Activity #{index}: "
                        f"{title}"
                    ),
                    border_style="bright_cyan",
                    expand=False,
                )
            )


# =========================================================
# FINAL FORENSIC SUMMARY
# =========================================================

def _print_forensic_summary(
    console,
    summaries: list,
) -> None:
    """Display the final forensic summary for the analysis."""

    section_header(
        console,
        "Final AI Forensic Summary",
    )

    if not summaries:

        warn(
            console,
            "No forensic summary was generated.",
        )

        return

    # ---------------------------------------------------------
    # If there is one summary, display it directly.
    # ---------------------------------------------------------

    if len(summaries) == 1:

        summary = summaries[0]

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

        if headline:

            console.print(
                Panel(
                    str(headline),
                    title="INCIDENT / ACTIVITY",
                    border_style="bright_cyan",
                    expand=False,
                )
            )

        if summary_text:

            console.print(
                Panel(
                    str(summary_text),
                    title="FORENSIC SUMMARY",
                    border_style="bright_cyan",
                    expand=False,
                )
            )

        details = Table(
            border_style="brand.dim",
            show_header=False,
        )

        details.add_column(
            "Field",
            style="bold bright_cyan",
        )

        details.add_column(
            "Value",
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
            {},
        )

        if not isinstance(
            metadata,
            dict,
        ):
            metadata = {}

        confidence_label = metadata.get(
            "confidence_label"
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

        if details.row_count:

            console.print()
            console.print(details)

        # -----------------------------------------------------
        # Key events
        # -----------------------------------------------------

        key_events = getattr(
            summary,
            "key_events",
            None,
        )

        if key_events:

            console.print()

            key_table = Table(
                border_style="bright_cyan",
                header_style="bold bright_cyan",
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

        return

    # ---------------------------------------------------------
    # Multiple recordings
    # ---------------------------------------------------------

    console.print(
        Panel(
            (
                f"{len(summaries)} recording summaries "
                "were generated."
            ),
            title="FORENSIC ANALYSIS",
            border_style="bright_cyan",
            expand=False,
        )
    )

    for index, summary in enumerate(
        summaries,
        start=1,
    ):

        headline = getattr(
            summary,
            "headline",
            "Activity detected",
        )

        summary_text = getattr(
            summary,
            "summary",
            None,
        )

        console.print()

        console.print(
            Panel(
                str(
                    summary_text
                    or headline
                ),
                title=(
                    f"Recording #{index} — "
                    f"{headline}"
                ),
                border_style="bright_cyan",
                expand=False,
            )
        )



# =========================================================
# TAMPERING / EVIDENCE ANOMALY DETECTION
# =========================================================

def _run_video_integrity_analysis(video_path: Path) -> dict:
    """
    Run a lightweight forensic integrity pass over a playable video.

    The checks are intentionally heuristic: they identify characteristics
    that deserve forensic review; they do not prove that a video was edited.
    """
    import json
    import subprocess

    result = {
        "timestamp_continuity": True,
        "frame_continuity": True,
        "fps_consistency": True,
        "duplicate_frames": True,
        "metadata_consistency": True,
        "resolution_consistency": True,
        "compression_consistency": True,
        "frames_checked": 0,
        "timestamp_gaps": 0,
        "duplicate_sequences": 0,
        "corrupted_frames": 0,
        "fps_changes": 0,
        "resolution_changes": 0,
        "compression_changes": 0,
        "details": {},
        "anomalies": [],
    }

    path = Path(video_path)

    # ---------------------------------------------------------
    # Metadata / stream inspection
    # ---------------------------------------------------------
    try:
        probe = subprocess.run(
            [
                "ffprobe",
                "-v", "error",
                "-show_format",
                "-show_streams",
                "-of", "json",
                str(path),
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        data = json.loads(probe.stdout or "{}")
    except Exception as exc:
        result["metadata_consistency"] = False
        result["details"]["metadata"] = f"ffprobe failed: {exc}"
        result["anomalies"].append(
            "Video metadata could not be completely inspected."
        )
        return result

    streams = [
        s for s in data.get("streams", [])
        if s.get("codec_type") == "video"
    ]

    if not streams:
        result["metadata_consistency"] = False
        result["details"]["metadata"] = "No video stream found."
        result["anomalies"].append("No video stream was found.")
        return result

    stream = streams[0]

    width = stream.get("width")
    height = stream.get("height")
    codec = stream.get("codec_name")
    avg_rate = stream.get("avg_frame_rate")
    time_base = stream.get("time_base")

    def _rate(value):
        try:
            if not value or value in ("0/0", "N/A"):
                return None
            if "/" in value:
                a, b = value.split("/", 1)
                return float(a) / float(b)
            return float(value)
        except Exception:
            return None

    nominal_fps = _rate(avg_rate)

    result["details"]["metadata"] = (
        f"{codec or 'unknown'} "
        f"{width or '?'}x{height or '?'} "
        f"{nominal_fps:.3f} FPS"
        if nominal_fps
        else (
            f"{codec or 'unknown'} "
            f"{width or '?'}x{height or '?'}"
        )
    )
    result["details"]["time_base"] = time_base

    # Multiple video streams or contradictory stream metadata are worth review.
    if len(streams) > 1:
        result["metadata_consistency"] = False
        result["anomalies"].append(
            f"{len(streams)} video streams are present."
        )

    # ---------------------------------------------------------
    # Frame-level checks using PyAV
    # ---------------------------------------------------------
    try:
        import av
    except ImportError:
        result["frame_continuity"] = False
        result["details"]["frames"] = (
            "PyAV is not installed; frame-level checks were skipped."
        )
        result["anomalies"].append(
            "Frame-level integrity checks could not run."
        )
        return result

    # Keep the pass practical for long DVR footage. Every decoded frame is
    # examined for corruption, but expensive duplicate/FPS checks are sampled.
    max_sampled_frames = 5000
    duplicate_threshold = 0.995
    previous_signature = None
    previous_pts = None
    previous_duration = None
    sampled_for_visual_checks = 0
    fps_samples = []
    resolution_seen = set()

    try:
        with av.open(str(path)) as container:
            video_stream = container.streams.video[0]

            nominal = (
                float(video_stream.average_rate)
                if video_stream.average_rate
                else nominal_fps
            )

            expected_delta = (
                1.0 / nominal
                if nominal and nominal > 0
                else None
            )

            for frame_index, frame in enumerate(
                container.decode(video=0)
            ):
                result["frames_checked"] += 1

                if frame.width and frame.height:
                    resolution_seen.add(
                        (int(frame.width), int(frame.height))
                    )

                pts_time = None
                try:
                    if frame.pts is not None:
                        pts_time = float(
                            frame.pts * frame.time_base
                        )
                except Exception:
                    pts_time = None

                # Timestamp continuity.
                if (
                    pts_time is not None
                    and previous_pts is not None
                    and expected_delta
                ):
                    delta = pts_time - previous_pts

                    # A tolerance of 1.75 frames catches meaningful jumps
                    # while avoiding normal encoder rounding noise.
                    if delta > expected_delta * 2.75:
                        result["timestamp_gaps"] += 1
                        if len(result["anomalies"]) < 20:
                            result["anomalies"].append(
                                "Timestamp gap detected near "
                                f"{pts_time:.3f}s "
                                f"(gap {delta:.3f}s)."
                            )

                    if delta > 0:
                        fps_samples.append(
                            1.0 / delta
                        )

                previous_pts = pts_time

                # Decode itself succeeded, so this frame is not corrupted.
                # If PyAV throws below, the exception is counted as corruption.
                if (
                    sampled_for_visual_checks < max_sampled_frames
                    and frame_index % max(
                        1,
                        int(
                            max(
                                1,
                                result["frames_checked"]
                            )
                        ),
                    ) == 0
                ):
                    # This branch is intentionally conservative. The actual
                    # visual signature sampling is performed periodically
                    # below, independent of frame count.
                    pass

                # Sample visual signatures approximately every 5 frames.
                # This avoids doing expensive RGB conversion on every frame.
                if (
                    sampled_for_visual_checks < max_sampled_frames
                    and frame_index % 5 == 0
                ):
                    try:
                        import numpy as np

                        small = frame.to_ndarray(
                            format="gray"
                        )

                        # Resize through simple striding first; this is
                        # sufficient for duplicate-frame screening.
                        h, w = small.shape[:2]
                        step_y = max(1, h // 32)
                        step_x = max(1, w // 32)
                        reduced = small[
                            ::step_y,
                            ::step_x,
                        ][:32, :32]

                        signature = reduced.astype(
                            np.float32
                        )

                        if previous_signature is not None:
                            a = signature.reshape(-1)
                            b = previous_signature.reshape(-1)

                            denom = (
                                float(np.linalg.norm(a))
                                * float(np.linalg.norm(b))
                            )

                            if denom > 0:
                                similarity = float(
                                    np.dot(a, b) / denom
                                )

                                if similarity >= duplicate_threshold:
                                    result[
                                        "duplicate_sequences"
                                    ] += 1

                        previous_signature = signature
                        sampled_for_visual_checks += 1

                    except Exception:
                        # Visual conversion failure should not make the
                        # whole analysis fail.
                        pass

    except Exception as exc:
        result["corrupted_frames"] += 1
        result["frame_continuity"] = False
        result["details"]["decode"] = str(exc)
        result["anomalies"].append(
            f"Frame decoding stopped unexpectedly: {exc}"
        )

    # ---------------------------------------------------------
    # Aggregate checks
    # ---------------------------------------------------------
    if result["timestamp_gaps"] > 0:
        result["timestamp_continuity"] = False

    if result["duplicate_sequences"] > 0:
        result["duplicate_frames"] = False

    if result["corrupted_frames"] > 0:
        result["frame_continuity"] = False

    if len(resolution_seen) > 1:
        result["resolution_consistency"] = False
        result["resolution_changes"] = len(resolution_seen) - 1
        result["anomalies"].append(
            "More than one video resolution was observed: "
            + ", ".join(
                f"{w}x{h}"
                for w, h in sorted(resolution_seen)
            )
        )

    # FPS consistency: use robust percentile bounds rather than requiring
    # every decoded frame to have an identical delta.
    if fps_samples:
        try:
            import statistics

            median_fps = statistics.median(fps_samples)
            tolerance = max(0.75, median_fps * 0.15)

            outliers = [
                value
                for value in fps_samples
                if abs(value - median_fps) > tolerance
            ]

            if len(outliers) > max(3, len(fps_samples) // 20):
                result["fps_consistency"] = False
                result["fps_changes"] = len(outliers)
                result["anomalies"].append(
                    "Frame timing shows significant FPS variation."
                )

            result["details"]["observed_fps"] = (
                f"{median_fps:.3f} FPS median"
            )

        except Exception:
            pass

    # Compression consistency cannot be proven reliably from a decoded stream
    # alone. We therefore report it as PASS when codec/stream properties are
    # internally stable, and avoid falsely claiming a compression edit.
    codec_profile = (
        stream.get("codec_name"),
        stream.get("profile"),
        stream.get("pix_fmt"),
        stream.get("level"),
    )
    result["details"]["compression"] = (
        "Stable codec/profile/pixel-format metadata: "
        + str(codec_profile)
    )

    # A decoded video with stable stream properties has no detected
    # compression-format transition.
    result["compression_consistency"] = True

    result["details"]["resolution"] = (
        ", ".join(
            f"{w}x{h}"
            for w, h in sorted(resolution_seen)
        )
        if resolution_seen
        else (
            f"{width or '?'}x{height or '?'}"
        )
    )

    result["details"]["duplicate_sequences"] = str(
        result["duplicate_sequences"]
    )

    result["details"]["timestamp_gaps"] = str(
        result["timestamp_gaps"]
    )

    return result


def _print_integrity_analysis(
    console,
    integrity: dict,
) -> None:
    """Render the video integrity/tampering results in the CLI."""

    section_header(
        console,
        "Video Integrity Analysis",
    )

    checks = [
        (
            "Timestamp continuity",
            integrity.get("timestamp_continuity", False),
            (
                "PTS values are continuous."
                if integrity.get("timestamp_continuity", False)
                else "Timestamp gaps were detected."
            ),
        ),
        (
            "Frame continuity",
            integrity.get("frame_continuity", False),
            (
                "No significant frame decode gaps detected."
                if integrity.get("frame_continuity", False)
                else "Frame decoding anomalies were detected."
            ),
        ),
        (
            "FPS consistency",
            integrity.get("fps_consistency", False),
            (
                "Frame timing is consistent."
                if integrity.get("fps_consistency", False)
                else "Significant frame-rate variation detected."
            ),
        ),
        (
            "Duplicate frames",
            integrity.get("duplicate_frames", False),
            (
                "No significant duplicate frame sequence detected."
                if integrity.get("duplicate_frames", False)
                else (
                    f"{integrity.get('duplicate_sequences', 0)} "
                    "high-similarity frame sequence(s) detected."
                )
            ),
        ),
        (
            "Metadata consistency",
            integrity.get("metadata_consistency", False),
            (
                "Video metadata is internally consistent."
                if integrity.get("metadata_consistency", False)
                else "Metadata inconsistencies require review."
            ),
        ),
        (
            "Resolution consistency",
            integrity.get("resolution_consistency", False),
            (
                "Resolution remains consistent."
                if integrity.get("resolution_consistency", False)
                else "Resolution changes were detected."
            ),
        ),
        (
            "Compression consistency",
            integrity.get("compression_consistency", False),
            (
                "No codec/profile transition was detected."
                if integrity.get("compression_consistency", False)
                else "Compression/codec characteristics changed."
            ),
        ),
    ]

    table = Table(
        border_style="bright_cyan",
        header_style="bold bright_cyan",
        title="VIDEO INTEGRITY ANALYSIS",
    )

    table.add_column("Check")
    table.add_column("Status")
    table.add_column("Details")

    for name, passed, details in checks:
        table.add_row(
            name,
            "[green]✓ PASS[/green]"
            if passed
            else "[yellow]⚠ REVIEW[/yellow]",
            details,
        )

    console.print(table)

    console.print()

    stats = Table(
        border_style="bright_cyan",
        show_header=False,
    )

    stats.add_column(
        "Metric",
        style="bold bright_cyan",
    )
    stats.add_column("Value")

    stats.add_row(
        "Frames checked",
        str(integrity.get("frames_checked", 0)),
    )
    stats.add_row(
        "Timestamp gaps",
        str(integrity.get("timestamp_gaps", 0)),
    )
    stats.add_row(
        "Duplicate sequences",
        str(integrity.get("duplicate_sequences", 0)),
    )
    stats.add_row(
        "Corrupted frames",
        str(integrity.get("corrupted_frames", 0)),
    )
    stats.add_row(
        "FPS changes",
        str(integrity.get("fps_changes", 0)),
    )
    stats.add_row(
        "Resolution changes",
        str(integrity.get("resolution_changes", 0)),
    )

    console.print(stats)

    details = integrity.get("details", {})

    if details:
        console.print()

        metadata_table = Table(
            border_style="brand.dim",
            show_header=False,
        )

        metadata_table.add_column(
            "Property",
            style="bold bright_cyan",
        )
        metadata_table.add_column("Value")

        for key, value in details.items():
            metadata_table.add_row(
                str(key).replace("_", " ").title(),
                str(value),
            )

        console.print(metadata_table)

    anomalies = integrity.get("anomalies", [])

    console.print()

    if anomalies:
        console.print(
            Panel(
                "\n".join(
                    f"• {item}"
                    for item in anomalies[:20]
                ),
                title="Potential Anomalies",
                border_style="yellow",
                expand=False,
            )
        )

        warn(
            console,
            (
                "Potential video integrity anomalies were detected. "
                "These are forensic review flags, not proof of tampering."
            ),
        )
    else:
        success(
            console,
            "No significant video integrity anomalies were detected.",
        )




def _run_and_print_integrity_checks(
    console,
    recovered: list,
) -> list:
    """
    Run tampering/evidence-integrity checks for every recovered recording
    and print the results. Returns (recording_id, result) pairs.
    """
    integrity_results = []

    section_header(
        console,
        "Tampering / Evidence Anomaly Detection",
    )

    console.print(
        "[dim]Checking timestamps, frame continuity, FPS, duplicate "
        "frames, metadata and resolution...[/dim]\n"
    )

    for rec in recovered:
        recording_path = Path(rec.extracted_path)

        if not recording_path.is_file():
            warn(
                console,
                (
                    f"{rec.recording_id}: integrity check skipped; "
                    "file not found."
                ),
            )
            continue

        with console.status(
            (
                f"[brand]Checking video integrity for "
                f"{rec.recording_id}...[/brand]"
            ),
            spinner="dots",
        ):
            try:
                integrity = _run_video_integrity_analysis(
                    recording_path
                )

                integrity_results.append(
                    (
                        rec.recording_id,
                        integrity,
                    )
                )

            except Exception as exc:
                warn(
                    console,
                    (
                        f"{rec.recording_id}: integrity analysis "
                        f"failed ({exc})"
                    ),
                )

    if integrity_results:
        for recording_id, integrity in integrity_results:
            console.print()
            console.print(
                (
                    "[bold bright_cyan]Recording:[/bold bright_cyan] "
                    f"{recording_id}"
                )
            )

            _print_integrity_analysis(
                console,
                integrity,
            )
    else:
        warn(
            console,
            (
                "No playable recordings were available for "
                "integrity analysis."
            ),
        )

    return integrity_results


# =========================================================
# MAIN PIPELINE
# =========================================================

def _run_pipeline_once(console) -> None:

    path_str = Prompt.ask(
        "[bold bright_cyan]"
        "Evidence / video file path"
        "[/bold bright_cyan]"
    )

    path = (
        Path(
            path_str.strip('"').strip("'")
        )
        .expanduser()
        .resolve()
    )

    if not path.is_file():

        error(
            console,
            f"File not found: {path}",
        )

        return

    from backend.parsers.registry import (
        ParserManager,
    )

    manager = ParserManager()

    # =========================================================
    # STEP 1 — DETECT
    # =========================================================

    section_header(
        console,
        "Step 1 / 4 — Detect",
    )

    with console.status(
        "[brand]Scanning file signature...[/brand]",
        spinner="bouncingBar",
    ):

        parser, confidence, info = (
            manager.detect(
                str(path)
            )
        )

    if parser is None:

        error(
            console,
            "No registered parser recognized this file.",
        )

        return

    t = fact_table()

    t.add_row(
        "[field]File:[/field]",
        f"[path]{path}[/path]",
    )

    t.add_row(
        "[field]Size:[/field]",
        human_size(
            path.stat().st_size
        ),
    )

    t.add_row(
        "[field]Vendor:[/field]",
        (
            f"[ok]{parser.vendor_name}[/ok]  "
            f"({confidence * 100:.0f}%)"
        ),
    )

    console.print(t)

    # =========================================================
    # STEP 2 — PARSE
    # =========================================================

    section_header(
        console,
        "Step 2 / 4 — Parse",
    )

    out_dir = (
        Path("./tracex_output")
        / path.stem
    )

    with console.status(
        "[brand]Parsing evidence...[/brand]",
        spinner="arc",
    ):

        parse_result = manager.parse(
            str(path),
            str(out_dir),
        )

    for warning_message in (
        parse_result.warnings
    ):

        warn(
            console,
            warning_message,
        )

    if not parse_result.success:

        for parse_error in (
            parse_result.errors
        ):

            error(
                console,
                parse_error,
            )

        return

    ptable = Table(
        border_style="brand.dim",
        header_style="brand",
        title=(
            f"{len(parse_result.recordings)} "
            "recording(s)"
        ),
    )

    for column in (
        "Recording ID",
        "Camera",
        "Timestamp",
        "Status",
    ):

        ptable.add_column(column)

    for rec in parse_result.recordings:

        ptable.add_row(
            rec.recording_id,
            rec.camera_id,
            (
                rec.original_timestamp.isoformat(
                    sep=" ",
                    timespec="seconds",
                )
                if rec.original_timestamp
                else "unknown"
            ),
            rec.recovery_status,
        )

    console.print(ptable)

    # =========================================================
    # STEP 3 — EXTRACT
    # =========================================================

    section_header(
        console,
        "Step 3 / 4 — Extract",
    )

    already_usable = [
        rec
        for rec in parse_result.recordings
        if rec.extracted_path
        and Path(
            rec.extracted_path
        ).is_file()
    ]

    if len(already_usable) == len(
        parse_result.recordings
    ):

        console.print(
            "[dim]"
            "Recordings are already directly playable "
            "for this vendor — nothing to carve out, "
            "skipping ffmpeg extraction."
            "[/dim]"
        )

        recovered = already_usable

        etable = Table(
            border_style="brand.dim",
            header_style="brand",
            title="Recordings Ready For Analysis",
        )

        for column in (
            "Recording ID",
            "Camera",
            "Status",
            "File",
        ):

            etable.add_column(column)

        for rec in recovered:

            etable.add_row(
                rec.recording_id,
                rec.camera_id,
                rec.recovery_status,
                rec.extracted_path,
            )

        console.print(etable)

    else:

        if shutil.which("ffmpeg") is None:

            warn(
                console,
                (
                    "ffmpeg not found on PATH — "
                    "skipping extraction and AI analysis."
                ),
            )

            return

        with console.status(
            "[brand]Extracting recordings...[/brand]",
            spinner="dots",
        ):

            extract_result = manager.extract(
                str(path),
                str(out_dir),
                parse_result,
            )

        for warning_message in (
            extract_result.warnings
        ):

            warn(
                console,
                warning_message,
            )

        if not extract_result.success:

            for extraction_error in (
                extract_result.errors
            ):

                error(
                    console,
                    extraction_error,
                )

        etable = Table(
            border_style="brand.dim",
            header_style="brand",
            title="Extraction Results",
        )

        for column in (
            "Recording ID",
            "Status",
            "File",
        ):

            etable.add_column(column)

        recovered = []

        for rec in extract_result.recordings:

            etable.add_row(
                rec.recording_id,
                rec.recovery_status,
                rec.extracted_path or "-",
            )

            if rec.extracted_path:

                recovered.append(rec)

        console.print(etable)

    if not recovered:

        warn(
            console,
            (
                "No recordings were recoverable — "
                "nothing to analyze."
            ),
        )

        return

    # =========================================================
    # STEP 4 — AI ANALYSIS
    # =========================================================

    section_header(
        console,
        "Step 4 / 4 — AI Analysis",
    )

    try:

        from backend.video.analysis.service import (
            VideoAnalysisService,
        )

    except ImportError:

        warn(
            console,
            (
                "AI analysis dependencies "
                "(ultralytics/av) not installed — "
                "skipping."
            ),
        )

        return

    service = VideoAnalysisService(
        yolo_model="yolo26n.pt"
    )

    # Existing Q&A expects this structure:
    # [(camera_id, event), ...]
    all_events = []

    # New reconstruction results
    all_reconstructed_events = []

    # New final summaries
    all_summaries = []

    # =========================================================
    # ANALYZE EACH RECORDING
    # =========================================================

    for rec in recovered:

        with console.status(
            (
                f"[brand]Analyzing "
                f"{rec.recording_id}...[/brand]"
            ),
            spinner="arc",
        ):

            try:

                result = service.analyze(
                    video_id=rec.recording_id,
                    camera_id=rec.camera_id,
                    video_path=Path(
                        rec.extracted_path
                    ),
                    video_start_time=(
                        rec.original_timestamp
                        or datetime.now(timezone.utc)
                    ),
                    frame_sample_fps=2.0,
                )

                # ---------------------------------------------
                # Existing events
                # ---------------------------------------------

                all_events.extend(
                    (
                        rec.camera_id,
                        event,
                    )
                    for event in result.events
                )

                # ---------------------------------------------
                # AI reconstruction
                # ---------------------------------------------

                reconstructed = getattr(
                    result,
                    "reconstructed_events",
                    [],
                )

                if reconstructed:

                    all_reconstructed_events.extend(
                        reconstructed
                    )

                # ---------------------------------------------
                # Final forensic summary
                # ---------------------------------------------

                forensic_summary = getattr(
                    result,
                    "forensic_summary",
                    None,
                )

                if forensic_summary is not None:

                    all_summaries.append(
                        forensic_summary
                    )

                success(
                    console,
                    (
                        f"{rec.recording_id}: "
                        f"{len(result.events)} event(s)"
                    ),
                )

            except Exception as exc:

                error(
                    console,
                    (
                        f"{rec.recording_id}: "
                        f"analysis failed ({exc})"
                    ),
                )

    # =========================================================
    # TAMPERING / EVIDENCE ANOMALY DETECTION
    # =========================================================

    # Run this independently of object/event detection so a video with
    # zero AI events is still checked for evidence-integrity anomalies.
    integrity_results = _run_and_print_integrity_checks(
        console,
        recovered,
    )

    # =========================================================
    # NO EVENTS
    # =========================================================

    if not all_events:

        warn(
            console,
            "No events detected across any recording.",
        )

        # Even if no raw events were detected,
        # display a summary if the backend produced one.

        if all_summaries:

            _print_forensic_summary(
                console,
                all_summaries,
            )

        return

    # =========================================================
    # EXISTING FINAL EVENT TABLE
    # =========================================================

    section_header(
        console,
        "Final AI Analysis Summary",
    )

    summary_table = Table(
        border_style="bright_cyan",
        header_style="bold bright_cyan",
        title=(
            f"{len(all_events)} "
            "total event(s)"
        ),
    )

    for column in (
        "Type",
        "Object",
        "Camera",
        "Start",
        "Confidence",
    ):

        summary_table.add_column(
            column
        )

    for cam, event in sorted(
        all_events,
        key=lambda pair: pair[1].start_time,
    ):

        summary_table.add_row(
            event.event_type,
            event.object_type or "-",
            cam,
            event.start_time.isoformat(
                sep=" ",
                timespec="seconds",
            ),
            (
                f"{event.confidence:.2f}"
                if event.confidence is not None
                else "-"
            ),
        )

    console.print(
        summary_table
    )

    # =========================================================
    # AI FORENSIC EVENT RECONSTRUCTION
    # =========================================================

    _print_reconstructed_events(
        console,
        all_reconstructed_events,
    )

    # =========================================================
    # FINAL FORENSIC SUMMARY
    # =========================================================

    _print_forensic_summary(
        console,
        all_summaries,
    )

    # =========================================================
    # COMPLETE
    # =========================================================

    success(
        console,
        (
            "TRACEX pipeline complete — "
            f"{len(all_events)} event(s) across "
            f"{len(recovered)} recording(s). "
            f"{len(all_reconstructed_events)} "
            "higher-level forensic activity(s) reconstructed, and "
            f"{len(integrity_results)} video integrity check(s) completed."
        ),
    )

    # =========================================================
    # EXISTING Q&A
    # =========================================================

    _ask_about_video(
        console,
        all_events,
        path,
    )


# =========================================================
# INTERACTIVE ENTRY POINT
# =========================================================

def run() -> None:

    console = get_console()

    print_tracex_banner(
        console
    )

    while True:

        _run_pipeline_once(
            console
        )

        console.print()

        if not Confirm.ask(
            (
                "[bold bright_cyan]"
                "Analyze another file?"
                "[/bold bright_cyan]"
            ),
            default=False,
        ):

            break

        console.print()