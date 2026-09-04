"""
OpenCV Forensic Trajectory & Event Reconstructor.

Reconstructs forensic timelines, trajectory direction vectors, loitering incidents,
sudden speed changes, and entry/exit activities from OpenCV tracked detections.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from backend.video.reconstruction.models import (
    ForensicSummary,
    ReconstructedEvent,
)


def _direction_from_vector(vx: float, vy: float) -> str:
    """Calculate 8-point compass direction from velocity vector (vx, vy)."""
    speed = math.hypot(vx, vy)
    if speed < 5.0:
        return "Stationary"

    # Angle in degrees (0 = East, 90 = South in image coordinates, 180 = West, 270 = North)
    angle = math.degrees(math.atan2(vy, vx)) % 360

    if 337.5 <= angle or angle < 22.5:
        return "Eastbound (→)"
    elif 22.5 <= angle < 67.5:
        return "South-East (↘)"
    elif 67.5 <= angle < 112.5:
        return "Southbound (↓)"
    elif 112.5 <= angle < 157.5:
        return "South-West (↙)"
    elif 157.5 <= angle < 202.5:
        return "Westbound (←)"
    elif 202.5 <= angle < 247.5:
        return "North-West (↖)"
    elif 247.5 <= angle < 292.5:
        return "Northbound (↑)"
    else:
        return "North-East (↗)"


@dataclass
class TrackObservation:
    frame_number: int
    timestamp_seconds: float
    bbox: tuple[float, float, float, float]
    velocity: tuple[float, float]
    confidence: float


@dataclass
class TrackSummary:
    track_id: int
    class_name: str
    first_seen: float
    last_seen: float
    duration_seconds: float
    observations: list[TrackObservation]
    start_point: tuple[float, float]
    end_point: tuple[float, float]
    total_displacement: float
    average_speed: float
    direction: str
    is_loitering: bool = False
    has_sudden_change: bool = False


class OpenCVForensicReconstructor:
    """Mathematical trajectory and forensic event reconstructor."""

    def __init__(
        self,
        loitering_min_seconds: float = 3.0,
        loitering_max_radius: float = 60.0,
        sudden_speed_delta_threshold: float = 40.0,
    ):
        self.loitering_min_seconds = loitering_min_seconds
        self.loitering_max_radius = loitering_max_radius
        self.sudden_speed_delta_threshold = sudden_speed_delta_threshold

    def reconstruct_from_detections(
        self,
        detections_by_frame: list[tuple[float, list[Any]]],  # [(timestamp_sec, [detections]), ...]
        video_start_time: datetime | None = None,
        video_id: str = "unknown",
        camera_id: str = "unknown",
    ) -> tuple[list[ReconstructedEvent], ForensicSummary]:
        """
        Reconstruct higher-level forensic events and summary from timestamped OpenCV detections.
        """
        base_time = video_start_time or datetime.now(timezone.utc)

        # 1. Group observations by track_id
        tracks: dict[int, list[tuple[float, Any]]] = {}
        for ts, frame_dets in detections_by_frame:
            for d in frame_dets:
                tid = getattr(d, "track_id", None)
                if tid is not None:
                    tracks.setdefault(tid, []).append((ts, d))

        track_summaries: list[TrackSummary] = []
        reconstructed_events: list[ReconstructedEvent] = []

        # 2. Analyze trajectories for each tracked entity
        for tid, obs_list in tracks.items():
            if not obs_list:
                continue

            first_det = obs_list[0][1]
            cname = (
                getattr(first_det, "object_type", None)
                or getattr(first_det, "class_name", None)
                or "object"
            ).lower()
            first_ts = obs_list[0][0]
            last_ts = obs_list[-1][0]
            dur = max(0.1, last_ts - first_ts)

            # Extract centroids
            centroids: list[tuple[float, float]] = []
            speeds: list[float] = []
            observations: list[TrackObservation] = []

            for idx, (ts, d) in enumerate(obs_list):
                bx = getattr(d, "bbox", (0, 0, 0, 0))
                cx = (bx[0] + bx[2]) / 2.0
                cy = (bx[1] + bx[3]) / 2.0
                centroids.append((cx, cy))
                vel = getattr(d, "velocity", (0.0, 0.0))

                # If detector velocity is 0.0, calculate instantaneous velocity from consecutive frame centroids
                if math.hypot(vel[0], vel[1]) < 0.1 and idx > 0:
                    prev_cx, prev_cy = centroids[idx - 1]
                    prev_ts = obs_list[idx - 1][0]
                    dt_f = max(0.05, ts - prev_ts)
                    vel = ((cx - prev_cx) / dt_f, (cy - prev_cy) / dt_f)

                v_speed = math.hypot(vel[0], vel[1])
                if v_speed > 0.0:
                    speeds.append(v_speed)

                observations.append(TrackObservation(
                    frame_number=int(getattr(d, "frame_number", 0)),
                    timestamp_seconds=ts,
                    bbox=bx,
                    velocity=vel,
                    confidence=float(getattr(d, "confidence", 0.7)),
                ))

            start_pt = centroids[0]
            end_pt = centroids[-1]
            displacement = math.hypot(end_pt[0] - start_pt[0], end_pt[1] - start_pt[1])
            disp_speed = displacement / dur if dur > 0 else 0.0
            avg_speed = max(disp_speed, (sum(speeds) / len(speeds)) if speeds else 0.0)
            overall_vx = (end_pt[0] - start_pt[0]) / dur
            overall_vy = (end_pt[1] - start_pt[1]) / dur
            direction = _direction_from_vector(overall_vx, overall_vy) if (displacement >= 15.0 or avg_speed >= 5.0) else "Stationary"

            # Check Loitering: present for >= threshold seconds with small overall displacement
            is_loitering = (dur >= self.loitering_min_seconds and displacement <= self.loitering_max_radius)

            # Check Sudden Speed Changes (acceleration / braking)
            has_sudden_change = False
            for i in range(1, len(speeds)):
                if abs(speeds[i] - speeds[i - 1]) >= self.sudden_speed_delta_threshold:
                    has_sudden_change = True
                    break

            summary = TrackSummary(
                track_id=tid,
                class_name=cname,
                first_seen=first_ts,
                last_seen=last_ts,
                duration_seconds=dur,
                observations=observations,
                start_point=start_pt,
                end_point=end_pt,
                total_displacement=displacement,
                average_speed=avg_speed,
                direction=direction,
                is_loitering=is_loitering,
                has_sudden_change=has_sudden_change,
            )
            track_summaries.append(summary)

            # 3. Generate structured forensic events
            start_dt = base_time + timedelta(seconds=first_ts)
            end_dt = base_time + timedelta(seconds=last_ts)

            # Entity presence & trajectory event
            reconstructed_events.append(ReconstructedEvent(
                video_id=video_id,
                camera_id=camera_id,
                event_type=f"{cname.upper()}_TRACK",
                start_time=start_dt,
                end_time=end_dt,
                confidence=max(o.confidence for o in observations),
                objects=[cname],
                title=f"{cname.capitalize()} #{tid} Active in Scene",
                description=(
                    f"Observed {cname} (ID #{tid}) for {dur:.1f}s. "
                    f"Trajectory: {direction}, avg speed: {avg_speed:.1f} px/s, "
                    f"displacement: {displacement:.0f} px."
                ),
                metadata={
                    "track_id": tid,
                    "direction": direction,
                    "avg_speed": avg_speed,
                    "displacement": displacement,
                },
            ))

            # Loitering / Prowling event
            if is_loitering and cname in ("person", "vehicle"):
                reconstructed_events.append(ReconstructedEvent(
                    video_id=video_id,
                    camera_id=camera_id,
                    event_type="LOITERING_DETECTED",
                    start_time=start_dt,
                    end_time=end_dt,
                    confidence=0.88,
                    objects=[cname],
                    title=f"Suspicious Loitering / Prowling: {cname.capitalize()} #{tid}",
                    description=(
                        f"{cname.capitalize()} #{tid} remained within a {displacement:.0f}px radius "
                        f"for {dur:.1f} seconds without exiting the area (potential casing/loitering behavior)."
                    ),
                    metadata={"track_id": tid, "duration": dur, "displacement": displacement},
                ))

            # Rapid Egress / Fleeing (Theft escape / Sprinting)
            if cname == "person" and avg_speed >= 75.0 and displacement >= 80.0:
                reconstructed_events.append(ReconstructedEvent(
                    video_id=video_id,
                    camera_id=camera_id,
                    event_type="RAPID_EGRESS_FLEEING",
                    start_time=start_dt,
                    end_time=end_dt,
                    confidence=0.85,
                    objects=[cname],
                    title=f"Rapid Egress / Fleeing: Person #{tid}",
                    description=(
                        f"Person #{tid} exhibited high-velocity sprinting / fleeing trajectory "
                        f"({direction}, speed: {avg_speed:.1f} px/s, displacement: {displacement:.0f} px)."
                    ),
                    metadata={"track_id": tid, "speed": avg_speed, "direction": direction},
                ))

            # Sudden Acceleration / Braking
            if has_sudden_change:
                reconstructed_events.append(ReconstructedEvent(
                    video_id=video_id,
                    camera_id=camera_id,
                    event_type="SUDDEN_VELOCITY_CHANGE",
                    start_time=start_dt,
                    end_time=end_dt,
                    confidence=0.80,
                    objects=[cname],
                    title=f"Sudden Velocity Shift: {cname.capitalize()} #{tid}",
                    description=f"Significant acceleration or sudden stop detected on {cname} #{tid}.",
                    metadata={"track_id": tid},
                ))

            # Off-Hours / Nighttime Perimeter Breach Check
            if start_dt.hour < 6 or start_dt.hour >= 22:
                reconstructed_events.append(ReconstructedEvent(
                    video_id=video_id,
                    camera_id=camera_id,
                    event_type="OFF_HOURS_PERIMETER_BREACH",
                    start_time=start_dt,
                    end_time=end_dt,
                    confidence=0.85,
                    objects=[cname],
                    title=f"Off-Hours Perimeter Activity: {cname.capitalize()} #{tid}",
                    description=f"Unusual presence of {cname} #{tid} recorded during restricted nighttime hours ({start_dt.strftime('%H:%M:%S')}).",
                    metadata={"track_id": tid, "time": start_dt.isoformat()},
                ))

        # 4. Multi-Entity Forensic Cross-Analysis (Theft, Robbery, Group Intrusions, Getaway Coordination)
        person_tracks = [t for t in track_summaries if t.class_name == "person"]
        vehicle_tracks = [t for t in track_summaries if t.class_name in ("vehicle", "car", "truck", "motorcycle")]
        object_tracks = [t for t in track_summaries if t.class_name not in ("person", "vehicle", "car", "truck", "motorcycle", "motion")]

        # Pattern A: Multi-Person Convergence / Group Action (e.g. Group Robbery / Gang Intrusion)
        for i in range(len(person_tracks)):
            for j in range(i + 1, len(person_tracks)):
                p1, p2 = person_tracks[i], person_tracks[j]
                # Check temporal overlap
                overlap_start = max(p1.first_seen, p2.first_seen)
                overlap_end = min(p1.last_seen, p2.last_seen)
                if overlap_end >= overlap_start:
                    # Compute minimum distance across any concurrent observations
                    min_dist = float("inf")
                    for o1 in p1.observations:
                        for o2 in p2.observations:
                            if abs(o1.timestamp_seconds - o2.timestamp_seconds) <= 0.6:
                                c1 = ((o1.bbox[0] + o1.bbox[2]) / 2.0, (o1.bbox[1] + o1.bbox[3]) / 2.0)
                                c2 = ((o2.bbox[0] + o2.bbox[2]) / 2.0, (o2.bbox[1] + o2.bbox[3]) / 2.0)
                                d = math.hypot(c1[0] - c2[0], c1[1] - c2[1])
                                if d < min_dist:
                                    min_dist = d

                    if min_dist <= 150.0:
                        reconstructed_events.append(ReconstructedEvent(
                            video_id=video_id,
                            camera_id=camera_id,
                            event_type="MULTI_PERSON_CONVERGENCE",
                            start_time=base_time + timedelta(seconds=overlap_start),
                            end_time=base_time + timedelta(seconds=overlap_end),
                            confidence=0.82,
                            objects=["person"],
                            title=f"Multi-Person Convergence: Person #{p1.track_id} & #{p2.track_id}",
                            description=(
                                f"Persons #{p1.track_id} and #{p2.track_id} converged in close spatial proximity "
                                f"({min_dist:.0f}px apart) during overlapping timeline ({overlap_end - overlap_start:.1f}s)."
                            ),
                            metadata={"p1_id": p1.track_id, "p2_id": p2.track_id, "distance": min_dist},
                        ))

        # Pattern B: Suspect & Getaway Vehicle Coordination
        for p in person_tracks:
            for v in vehicle_tracks:
                # Vehicle present during or within 3 seconds after person activity
                time_diff = abs(v.last_seen - p.last_seen)
                if time_diff <= 4.0:
                    reconstructed_events.append(ReconstructedEvent(
                        video_id=video_id,
                        camera_id=camera_id,
                        event_type="SUSPECT_VEHICLE_COORDINATION",
                        start_time=base_time + timedelta(seconds=min(p.first_seen, v.first_seen)),
                        end_time=base_time + timedelta(seconds=max(p.last_seen, v.last_seen)),
                        confidence=0.84,
                        objects=["person", v.class_name],
                        title=f"Suspect & Vehicle Coordination: Person #{p.track_id} + {v.class_name.capitalize()} #{v.track_id}",
                        description=(
                            f"Person #{p.track_id} and {v.class_name} #{v.track_id} exhibited synchronized presence / departure "
                            f"(departure delta: {time_diff:.1f}s, vehicle heading: {v.direction}, speed: {v.average_speed:.1f} px/s)."
                        ),
                        metadata={"person_id": p.track_id, "vehicle_id": v.track_id, "time_delta": time_diff},
                    ))

        # Pattern C: Person Interaction with Static Asset followed by Disappearance (Larceny / Item Theft)
        for p in person_tracks:
            for obj in object_tracks:
                if obj.last_seen <= p.last_seen + 2.0:
                    dist = math.hypot(p.end_point[0] - obj.end_point[0], p.end_point[1] - obj.end_point[1])
                    if dist <= 100.0:
                        reconstructed_events.append(ReconstructedEvent(
                            video_id=video_id,
                            camera_id=camera_id,
                            event_type="SUSPICIOUS_ASSET_INTERACTION",
                            start_time=base_time + timedelta(seconds=obj.first_seen),
                            end_time=base_time + timedelta(seconds=p.last_seen),
                            confidence=0.80,
                            objects=["person", obj.class_name],
                            title=f"Possible Asset Removal / Theft: {obj.class_name.capitalize()} #{obj.track_id}",
                            description=(
                                f"Person #{p.track_id} was in close proximity ({dist:.0f}px) to {obj.class_name} #{obj.track_id} "
                                f"before the item ceased appearing in subsequent frames."
                            ),
                            metadata={"person_id": p.track_id, "object_id": obj.track_id, "object_type": obj.class_name},
                        ))

        # Pattern D: Vehicle-to-Vehicle Collision & T-Bone Impact Detection
        for i in range(len(vehicle_tracks)):
            for j in range(i + 1, len(vehicle_tracks)):
                v1, v2 = vehicle_tracks[i], vehicle_tracks[j]
                overlap_start = max(v1.first_seen, v2.first_seen)
                overlap_end = min(v1.last_seen, v2.last_seen)
                if overlap_end >= overlap_start:
                    min_dist = float("inf")
                    max_iou = 0.0
                    impact_ts = overlap_start

                    for o1 in v1.observations:
                        for o2 in v2.observations:
                            if abs(o1.timestamp_seconds - o2.timestamp_seconds) <= 0.6:
                                c1 = ((o1.bbox[0] + o1.bbox[2]) / 2.0, (o1.bbox[1] + o1.bbox[3]) / 2.0)
                                c2 = ((o2.bbox[0] + o2.bbox[2]) / 2.0, (o2.bbox[1] + o2.bbox[3]) / 2.0)
                                d = math.hypot(c1[0] - c2[0], c1[1] - c2[1])
                                if d < min_dist:
                                    min_dist = d
                                    impact_ts = o1.timestamp_seconds

                                ix1 = max(o1.bbox[0], o2.bbox[0])
                                iy1 = max(o1.bbox[1], o2.bbox[1])
                                ix2 = min(o1.bbox[2], o2.bbox[2])
                                iy2 = min(o1.bbox[3], o2.bbox[3])
                                iw = max(0.0, ix2 - ix1)
                                ih = max(0.0, iy2 - iy1)
                                inter = iw * ih
                                a1 = max(1.0, (o1.bbox[2] - o1.bbox[0]) * (o1.bbox[3] - o1.bbox[1]))
                                a2 = max(1.0, (o2.bbox[2] - o2.bbox[0]) * (o2.bbox[3] - o2.bbox[1]))
                                iou = inter / (a1 + a2 - inter) if (a1 + a2 - inter) > 0 else 0.0
                                if iou > max_iou:
                                    max_iou = iou

                    max_speed = max(v1.average_speed, v2.average_speed)
                    if (max_iou >= 0.05 or min_dist <= 130.0) and max_speed >= 15.0:
                        impact_dt = base_time + timedelta(seconds=impact_ts)
                        reconstructed_events.append(ReconstructedEvent(
                            video_id=video_id,
                            camera_id=camera_id,
                            event_type="VEHICLE_COLLISION_DETECTED",
                            start_time=impact_dt,
                            end_time=base_time + timedelta(seconds=overlap_end),
                            confidence=0.92,
                            objects=[v1.class_name, v2.class_name],
                            title=f"CRITICAL INCIDENT: Vehicle Collision / Impact Detected (Vehicle #{v1.track_id} & #{v2.track_id})",
                            description=(
                                f"Physical vehicle collision / impact detected between {v1.class_name} #{v1.track_id} "
                                f"(heading: {v1.direction}, pre-impact speed: {v1.average_speed:.1f} px/s) and {v2.class_name} #{v2.track_id} "
                                f"(heading: {v2.direction}, pre-impact speed: {v2.average_speed:.1f} px/s) at timeline offset {impact_ts:.1f}s. "
                                f"Minimum proximity: {min_dist:.0f}px, Max bounding overlap IoU: {max_iou:.2f}."
                            ),
                            metadata={
                                "v1_id": v1.track_id,
                                "v2_id": v2.track_id,
                                "impact_offset_seconds": impact_ts,
                                "min_distance": min_dist,
                                "max_iou": max_iou,
                                "is_critical_incident": True,
                            },
                        ))

        # Pattern E: Single Vehicle Crash / Severe Deceleration Impact
        for v in vehicle_tracks:
            if v.average_speed >= 40.0 and v.has_sudden_change:
                reconstructed_events.append(ReconstructedEvent(
                    video_id=video_id,
                    camera_id=camera_id,
                    event_type="VEHICLE_CRASH_IMPACT",
                    start_time=base_time + timedelta(seconds=v.first_seen),
                    end_time=base_time + timedelta(seconds=v.last_seen),
                    confidence=0.88,
                    objects=[v.class_name],
                    title=f"CRITICAL INCIDENT: Sudden Vehicle Crash / Impact: {v.class_name.capitalize()} #{v.track_id}",
                    description=(
                        f"{v.class_name.capitalize()} #{v.track_id} experienced catastrophic sudden deceleration / impact "
                        f"(pre-impact speed: {v.average_speed:.1f} px/s, heading: {v.direction})."
                    ),
                    metadata={"vehicle_id": v.track_id, "pre_speed": v.average_speed, "is_critical_incident": True},
                ))

        # 5. Generate overall forensic summary
        people_count = sum(1 for t in track_summaries if t.class_name == "person")
        vehicle_count = sum(1 for t in track_summaries if t.class_name in ("vehicle", "car", "truck", "motorcycle"))
        loiter_count = sum(1 for t in track_summaries if t.is_loitering)
        flee_count = sum(1 for e in reconstructed_events if e.event_type == "RAPID_EGRESS_FLEEING")
        coord_count = sum(1 for e in reconstructed_events if e.event_type == "SUSPECT_VEHICLE_COORDINATION")
        crash_count = sum(1 for e in reconstructed_events if "COLLISION" in e.event_type or "CRASH" in e.event_type)

        headline_parts = []
        if crash_count > 0:
            headline_parts.append(f"CRITICAL: Traffic Collision Flagged ({crash_count} Incident(s))")
        if people_count > 0:
            headline_parts.append(f"{people_count} Person(s)")
        if vehicle_count > 0:
            headline_parts.append(f"{vehicle_count} Vehicle(s)")
        if flee_count > 0:
            headline_parts.append("Rapid Fleeing Detected")
        if not headline_parts:
            headline_parts.append("Motion Activity")

        headline = f"Forensic Scene Analysis: {', '.join(headline_parts)}"

        summary_text = (
            f"OpenCV forensic reconstruction tracked {len(track_summaries)} distinct entities "
            f"({people_count} people, {vehicle_count} vehicles). "
        )
        if crash_count > 0:
            summary_text += f"CRITICAL ALERT: System identified {crash_count} vehicle collision/impact incident(s). "
        if flee_count > 0:
            summary_text += f"{flee_count} rapid egress/fleeing movement(s) detected. "
        if loiter_count > 0:
            summary_text += f"{loiter_count} loitering/prowling observation(s) identified. "
        if coord_count > 0:
            summary_text += f"{coord_count} suspect-vehicle coordination pattern(s) flagged. "
        if not (crash_count or flee_count or loiter_count or coord_count):
            summary_text += "Normal directional transit observed across timelines."

        start_dt = min((e.start_time for e in reconstructed_events), default=base_time)
        end_dt = max((e.end_time for e in reconstructed_events), default=base_time)

        # Highlight critical events at the top of key_events
        top_events = [e for e in reconstructed_events if getattr(e, "metadata", {}).get("is_critical_incident")]
        key_events_list = [
            f"CRITICAL: {e.title} at {e.start_time.strftime('%H:%M:%S') if hasattr(e.start_time, 'strftime') else str(e.start_time)}"
            for e in top_events[:3]
        ]
        key_events_list.extend([
            f"Tracked {t.class_name} #{t.track_id} moving {t.direction} (speed {t.average_speed:.1f} px/s)"
            for t in track_summaries[:5]
        ])

        forensic_summary = ForensicSummary(
            video_id=video_id,
            camera_id=camera_id,
            start_time=start_dt,
            end_time=end_dt,
            headline=headline,
            summary=summary_text,
            key_events=key_events_list,
            objects_detected=list({t.class_name for t in track_summaries}),
            event_count=len(reconstructed_events),
            confidence=0.95 if crash_count > 0 else (0.90 if track_summaries else 0.70),
            metadata={"total_tracks": len(track_summaries), "crash_count": crash_count},
        )

        return reconstructed_events, forensic_summary
