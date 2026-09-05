import json
from datetime import datetime, timedelta
from pathlib import Path

from backend.video.analysis.models import Detection
from backend.ai.events.event_builder import build_detection_events


JSON_PATH = Path(
    "test_output/ai_detections.json"
)


def main():

    print()
    print("==============================")
    print("      EVENT BUILDER TEST")
    print("==============================")

    if not JSON_PATH.exists():
        print("AI detection JSON not found:")
        print(JSON_PATH)
        return

    with open(
        JSON_PATH,
        "r",
        encoding="utf-8",
    ) as file:
        raw_detections = json.load(file)

    print()
    print("Raw detections:", len(raw_detections))

    # Temporary base time for testing.
    # Later this will come from the DVR/parser timestamp.
    base_time = datetime(
        2026,
        8,
        27,
        21,
        0,
        0,
    )

    detections = []

    for item in raw_detections:

        timestamp = (
            base_time
            + timedelta(
                seconds=item["timestamp_seconds"]
            )
        )

        bbox = tuple(
            float(value)
            for value in item["bbox"]
        )

        detection = Detection(
            video_id="test_video",
            camera_id="camera_01",
            frame_number=item["frame_number"],
            timestamp=timestamp,
            object_type=item["class_name"],
            confidence=item["confidence"],
            bbox=bbox,
            track_id=item.get("track_id"),
            metadata={
                "source": "opencv",
            },
        )

        detections.append(detection)

    print(
        "Detection objects created:",
        len(detections),
    )

    events = build_detection_events(
        detections,
        max_gap_seconds=3.0,
    )

    print()
    print("Events generated:", len(events))

    print()
    print("Forensic Events")
    print("------------------------------")

    for event in events:

        print(
            f"{event.event_type}"
            f" | "
            f"{event.start_time}"
            f" → "
            f"{event.end_time}"
            f" | "
            f"confidence="
            f"{event.confidence:.3f}"
            f" | "
            f"track="
            f"{event.track_id}"
        )

    print()
    print("==============================")
    print("        TEST COMPLETE")
    print("==============================")


if __name__ == "__main__":
    main()