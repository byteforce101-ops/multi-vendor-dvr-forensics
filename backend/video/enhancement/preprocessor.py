"""
OpenCV Surveillance Image Enhancement Preprocessor.

Applies Contrast Limited Adaptive Histogram Equalization (CLAHE),
adaptive gamma luminance correction, and unsharp masking to enhance
low-light, over-exposed, or grainy CCTV video footage before AI detection.
"""

from __future__ import annotations

import cv2
import numpy as np


def apply_clahe(
    bgr_image: np.ndarray,
    clip_limit: float = 2.5,
    tile_grid_size: tuple[int, int] = (8, 8),
) -> np.ndarray:
    """Apply CLAHE (Contrast Limited Adaptive Histogram Equalization) on L channel in LAB color space."""
    if bgr_image is None or bgr_image.size == 0:
        return bgr_image

    try:
        lab = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2LAB)
        l_channel, a_channel, b_channel = cv2.split(lab)

        clahe = cv2.createCLAHE(
            clipLimit=float(clip_limit),
            tileGridSize=tile_grid_size,
        )
        enhanced_l = clahe.apply(l_channel)

        merged = cv2.merge([enhanced_l, a_channel, b_channel])
        return cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)
    except Exception:
        return bgr_image


def auto_gamma_correction(
    bgr_image: np.ndarray,
    target_mean: float = 110.0,
) -> np.ndarray:
    """Automatically adjust gamma for under-exposed (night) or over-exposed CCTV frames."""
    if bgr_image is None or bgr_image.size == 0:
        return bgr_image

    try:
        gray = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2GRAY)
        current_mean = float(np.mean(gray))

        # If already in good dynamic range (70 - 170), no gamma adjustment needed
        if 70.0 <= current_mean <= 170.0:
            return bgr_image

        # If too dark (night surveillance)
        if current_mean < 70.0:
            # Avoid division by zero
            gamma = max(0.4, min(1.8, np.log(target_mean / 255.0) / np.log(max(1.0, current_mean) / 255.0)))
        else:
            # Overexposed glare
            gamma = max(0.6, min(2.0, np.log(target_mean / 255.0) / np.log(max(1.0, current_mean) / 255.0)))

        # Build lookup table for fast execution
        lut = np.array([np.clip(((i / 255.0) ** gamma) * 255.0, 0, 255) for i in range(256)]).astype("uint8")
        return cv2.LUT(bgr_image, lut)
    except Exception:
        return bgr_image


def unsharp_mask(
    bgr_image: np.ndarray,
    sigma: float = 1.0,
    strength: float = 0.5,
) -> np.ndarray:
    """Enhance edges and fine details of distant CCTV objects using Gaussian unsharp mask."""
    if bgr_image is None or bgr_image.size == 0:
        return bgr_image

    try:
        blurred = cv2.GaussianBlur(bgr_image, (0, 0), sigma)
        sharpened = cv2.addWeighted(bgr_image, 1.0 + strength, blurred, -strength, 0)
        return sharpened
    except Exception:
        return bgr_image


def enhance_surveillance_frame(
    bgr_image: np.ndarray,
    enable_clahe: bool = True,
    auto_gamma: bool = True,
    enable_sharpen: bool = False,
) -> np.ndarray:
    """
    Main enhancement pipeline for surveillance CCTV frames.
    
    Transforms raw video frames by normalizing exposure and boosting local contrast
    prior to feeding into neural network detectors.
    """
    if bgr_image is None or bgr_image.size == 0:
        return bgr_image

    enhanced = bgr_image

    if auto_gamma:
        enhanced = auto_gamma_correction(enhanced)

    if enable_clahe:
        enhanced = apply_clahe(enhanced)

    if enable_sharpen:
        enhanced = unsharp_mask(enhanced)

    return enhanced
