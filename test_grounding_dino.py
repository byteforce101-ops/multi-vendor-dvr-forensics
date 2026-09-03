from backend.ai.detectors.grounding_dino_detector import (
    GroundingDINODetector,
)


detector = GroundingDINODetector(
    confidence=0.20
)

detections = detector.detect(
    "test_image.jpg",
    [
        "person",
        "car",
        "motorcycle",
        "bicycle",
        "truck",
        "bus",
        "bag",
        "phone",
    ],
)

print()
print("=" * 50)
print(f"DETECTIONS FOUND: {len(detections)}")
print("=" * 50)

for detection in detections:
    print(
        f"Object: {detection['label']} | "
        f"Confidence: {detection['confidence']:.3f} | "
        f"Box: {detection['bbox']}"
    )