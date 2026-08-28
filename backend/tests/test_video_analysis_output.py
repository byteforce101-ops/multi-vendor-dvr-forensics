import json
from pathlib import Path

from backend.ai.detectors.yolo_detector import YOLODetector
from backend.video.extraction.frame_extractor import iter_frames


VIDEO_PATH = Path(
    r"E:\Downloads\WhatsApp Video 2026-08-27 at 9.39.49 PM.mp4"
)

OUTPUT_PATH = Path(
    "test_output/ai_detections.json"
)


def main():

    print()
    print("==============================")
    print("   VIDEO AI ANALYSIS TEST")
    print("==============================")

    detector = YOLODetector(
        model_path="yolo26n.pt",
        confidence=0.35,
    )

    all_detections = []

    for sample in iter_frames(
        VIDEO_PATH,
        sample_fps=5.0,
    ):

        detections = detector.track(
            sample.image
        )

        for detection in detections:

            record = {
                "frame_number": sample.frame_number,
                "timestamp_seconds": round(
                    sample.timestamp_seconds,
                    3,
                ),
                "class_id": detection["class_id"],
                "class_name": detection["class_name"],
                "confidence": round(
                    detection["confidence"],
                    4,
                ),
                "bbox": detection["bbox"],
                "track_id": detection["track_id"],
            }

            all_detections.append(record)

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with open(
        OUTPUT_PATH,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            all_detections,
            file,
            indent=2,
        )

    print()
    print(
        "Frames analyzed:",
        len(set(
            d["frame_number"]
            for d in all_detections
        )),
    )

    print(
        "Total detections:",
        len(all_detections),
    )

    print()
    print("Saved results to:")
    print(OUTPUT_PATH)

    print()
    print("==============================")
    print("        TEST COMPLETE")
    print("==============================")


if __name__ == "__main__":
    main()