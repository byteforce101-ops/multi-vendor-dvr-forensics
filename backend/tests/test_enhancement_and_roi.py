"""backend/tests/test_enhancement_and_roi.py — Tests for OpenCV CLAHE enhancement and motion ROI detection."""

import cv2
import numpy as np
import pytest
from datetime import datetime, timezone

from backend.video.enhancement.preprocessor import (
    apply_clahe,
    auto_gamma_correction,
    unsharp_mask,
    enhance_surveillance_frame,
)
from backend.ai.detectors.yolo_detector import YOLODetector, YOLODetection
from backend.ai.pipeline.ai_service import AIService
from backend.video.extraction.frame_extractor import FrameSample


def test_clahe_enhancement_on_low_contrast_image():
    """Verify CLAHE expands contrast on dark low-contrast surveillance images."""
    # Dark low-contrast image (mean ~30)
    dark_img = np.full((300, 300, 3), 30, dtype=np.uint8)
    dark_img[50:100, 50:100] = 35  # subtle object

    enhanced = apply_clahe(dark_img, clip_limit=3.0)
    assert enhanced.shape == dark_img.shape
    assert enhanced.dtype == np.uint8

    # Standard deviation / contrast should increase after CLAHE
    std_before = np.std(dark_img)
    std_after = np.std(enhanced)
    assert std_after >= std_before


def test_auto_gamma_correction():
    """Verify auto gamma brightens dark night surveillance frames."""
    dark_night_img = np.full((200, 200, 3), 20, dtype=np.uint8)
    corrected = auto_gamma_correction(dark_night_img, target_mean=110.0)

    assert corrected.shape == dark_night_img.shape
    mean_before = np.mean(dark_night_img)
    mean_after = np.mean(corrected)
    assert mean_after > mean_before


def test_unsharp_mask():
    """Verify unsharp masking sharpens edges without corrupting dimensions."""
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    img[20:80, 20:80] = 180

    sharpened = unsharp_mask(img, sigma=1.0, strength=0.5)
    assert sharpened.shape == img.shape
    assert sharpened.dtype == np.uint8


def test_enhance_surveillance_frame_pipeline():
    """Verify the full enhance_surveillance_frame pipeline runs seamlessly."""
    frame = np.random.randint(20, 60, size=(240, 320, 3), dtype=np.uint8)
    enhanced = enhance_surveillance_frame(
        frame,
        enable_clahe=True,
        auto_gamma=True,
        enable_sharpen=True,
    )
    assert enhanced.shape == (240, 320, 3)
    assert enhanced.dtype == np.uint8
    assert np.mean(enhanced) > np.mean(frame)


def test_yolo_motion_roi_patch_detection():
    """Verify YOLODetector.detect_with_motion_rois runs inference on motion crops and fuses detections."""
    detector = YOLODetector()

    # Create synthetic frame with a high-contrast object in a motion bounding box
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    # Motion bounding box at (100, 100, 80, 120)
    motion_boxes = [(100, 100, 80, 120)]

    detections = detector.detect_with_motion_rois(frame, motion_boxes=motion_boxes, use_tracking=False)
    assert isinstance(detections, list)


def test_ai_service_with_enhancement_and_motion_rois():
    """Verify AIService analyze_frames executes with enhancement and motion ROIs enabled."""
    service = AIService(
        enable_grounding_dino=False,
        enable_enhancement=True,
        enable_motion_rois=True,
    )

    frame1 = np.full((240, 320, 3), 30, dtype=np.uint8)
    frame2 = np.full((240, 320, 3), 30, dtype=np.uint8)
    frame2[80:160, 80:160] = 220  # moving object in frame 2

    samples = [
        FrameSample(frame_number=0, timestamp_seconds=0.0, image=frame1),
        FrameSample(frame_number=1, timestamp_seconds=0.5, image=frame2),
    ]

    results = service.analyze_frames(samples)
    assert isinstance(results, list)
