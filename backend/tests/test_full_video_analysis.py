from datetime import datetime
from pathlib import Path

from backend.video.analysis.service import (
    VideoAnalysisService,
)


VIDEO_PATH = Path(
    r"E:\Downloads\WhatsApp Video 2026-08-27 at 9.39.49 PM.mp4"
)


def main():

    print()
    print("==============================")
    print("   FULL VIDEO ANALYSIS TEST")
    print("==============================")

    print()
    print("Video:")
    print(VIDEO_PATH)

    if not VIDEO_PATH.exists():
        print()
        print("ERROR: Video does not exist.")
        return

    print()
    print("Starting analysis...")

    service = VideoAnalysisService(
        yolo_model="yolo26n.pt",
        ai_confidence=0.35,
        ai_iou=0.50,
    )

    result = service.analyze(
        video_id="test_video_001",
        camera_id="camera_01",
        video_path=VIDEO_PATH,
        video_start_time=datetime(
            2026,
            8,
            27,
            21,
            0,
            0,
        ),
        frame_sample_fps=5.0,
    )

    print()
    print("==============================")
    print("       ANALYSIS SUCCESS")
    print("==============================")

    print()
    print("Video Metadata")
    print("------------------------------")
    print("Duration:", result.metadata.duration_seconds)
    print("Resolution:",
          result.metadata.width,
          "x",
          result.metadata.height)
    print("FPS:", result.metadata.fps)
    print("Codec:", result.metadata.codec)

    print()
    print("Frames analyzed:",
          result.frame_count_analyzed)

    print()
    print("Events generated:",
          len(result.events))

    print()
    print("Events")
    print("------------------------------")

    for event in result.events:

        print(
            f"{event.event_type}"
            f" | "
            f"{event.start_time}"
            f" -> "
            f"{event.end_time}"
            f" | "
            f"confidence="
            f"{event.confidence}"
            f" | "
            f"track="
            f"{event.track_id}"
        )

    print()
    print("Timeline entries:",
          len(result.timeline))

    print()
    print("==============================")
    print("        TEST COMPLETE")
    print("==============================")


if __name__ == "__main__":
    main()