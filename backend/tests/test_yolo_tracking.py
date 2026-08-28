from pathlib import Path

import cv2

from backend.ai.detectors.yolo_detector import YOLODetector
from backend.video.extraction.frame_extractor import iter_frames


VIDEO_PATH = Path(
    r"E:\Downloads\WhatsApp Video 2026-08-27 at 9.39.49 PM.mp4"
)


def main():

    print()
    print("==============================")
    print("       YOLO TRACKING TEST")
    print("==============================")

    detector = YOLODetector(
        model_path="yolo26n.pt",
        confidence=0.35,
    )

    frame_count = 0

    for sample in iter_frames(
        VIDEO_PATH,
        sample_fps=5.0,
    ):

        detections = detector.track(
            sample.image
        )

        print(
            f"\nTime: "
            f"{sample.timestamp_seconds:.3f}s"
        )

        if not detections:
            print("  No detections")
        else:
            for detection in detections:

                print(
                    f"  "
                    f"{detection['class_name']} "
                    f"| confidence="
                    f"{detection['confidence']:.3f} "
                    f"| track="
                    f"{detection['track_id']}"
                )

        frame_count += 1

    print()
    print(
        "Frames analyzed:",
        frame_count
    )

    print()
    print("==============================")
    print("        TEST COMPLETE")
    print("==============================")


if __name__ == "__main__":
    main()