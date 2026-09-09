from pathlib import Path

import cv2

from backend.ai.detectors.tracex_vision_detector import TraceXVisionDetector


FRAME_PATH = Path(
    "test_output/frames/frame_00_0.000s.jpg"
)


def main():

    print()
    print("==============================")
    print("       TRACEX VISION DETECTION TEST")
    print("==============================")

    if not FRAME_PATH.exists():
        print("Frame does not exist:")
        print(FRAME_PATH)
        return

    print()
    print("Loading frame:")
    print(FRAME_PATH)

    frame = cv2.imread(
        str(FRAME_PATH)
    )

    if frame is None:
        print("Could not read frame.")
        return

    print("Frame loaded.")
    print("Shape:", frame.shape)

    print()
    print("Loading TraceX Vision model...")

    detector = TraceXVisionDetector(
        model_path="backend/models/tracex_vision.pt",
        confidence=0.35,
    )

    print("TraceX Vision loaded.")

    detections = detector.detect(
        frame
    )

    print()
    print("Detections:")
    print("------------------------------")

    if not detections:
        print("No objects detected.")

    for detection in detections:

        print(
            f"{detection['class_name']} "
            f"| confidence="
            f"{detection['confidence']:.3f} "
            f"| bbox="
            f"{detection['bbox']}"
        )

    print()
    print(
        "Total detections:",
        len(detections),
    )

    print()
    print("==============================")
    print("        TEST COMPLETE")
    print("==============================")


if __name__ == "__main__":
    main()