from __future__ import annotations

from backend.ai.tracking.entity_tracker import (
    Entity,
)


def build_disappearance_events(
    entities: list[Entity],
    video_id: str,
    camera_id: str,
    video_start_time,
    minimum_observations: int = 2,
):

    events = []

    for entity in entities:

        if len(
            entity.observations
        ) < minimum_observations:
            continue

        if not entity.observations:
            continue

        last = (
            entity.observations[-1]
        )

        first = (
            entity.observations[0]
        )

        last_timestamp = (
            video_start_time
            + __import__(
                "datetime"
            ).timedelta(
                seconds=(
                    last.timestamp_seconds
                )
            )
        )

        first_timestamp = (
            video_start_time
            + __import__(
                "datetime"
            ).timedelta(
                seconds=(
                    first.timestamp_seconds
                )
            )
        )

        events.append(
            {
                "video_id": video_id,
                "camera_id": camera_id,
                "event_type": (
                    "OBJECT_DISAPPEARED"
                ),
                "start_time": last_timestamp,
                "end_time": last_timestamp,
                "confidence": min(
                    1.0,
                    max(
                        0.30,
                        entity.confidence,
                    ),
                ),
                "track_id": (
                    entity.detector_track_id
                ),
                "entity_id": (
                    entity.entity_id
                ),
                "object_type": (
                    entity.object_type
                ),
                "metadata": {
                    "first_seen": (
                        first_timestamp.isoformat()
                    ),
                    "last_seen": (
                        last_timestamp.isoformat()
                    ),
                    "first_frame": (
                        entity.first_seen_frame
                    ),
                    "last_frame": (
                        entity.last_seen_frame
                    ),
                    "observation_count": (
                        len(
                            entity.observations
                        )
                    ),
                    "bbox": list(
                        last.bbox
                    ),
                    "sources": sorted(
                        {
                            source
                            for observation
                            in entity.observations
                            for source
                            in observation.sources
                        }
                    ),
                },
            }
        )

    return events