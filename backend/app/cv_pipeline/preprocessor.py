# ============================================================
# cv_pipeline/preprocessor.py — Image Preprocessing
# ============================================================
# Stage 2 of the CV pipeline.
#
# Takes a raw floor plan image (NumPy array from OpenCV) and
# returns a clean, binarised image ready for line/contour
# detection.
#
# Steps:
#   1. Convert to grayscale
#   2. Resize if too large (memory safety for 8 GB RAM)
#   3. Remove noise with Gaussian blur
#   4. Adaptive thresholding → clean black-on-white binary image
#   5. Deskew (correct slight rotation from scanning)
# ============================================================

import cv2
import numpy as np
from typing import Tuple


# Maximum image dimension — larger images are resized down
# 2000 px fits comfortably within our 8 GB RAM budget
MAX_DIMENSION = 2000


def preprocess(image: np.ndarray) -> Tuple[np.ndarray, np.ndarray, float]:
    """
    Clean and binarise a floor plan image for CV processing.

    Args:
        image:  BGR image loaded by OpenCV (H×W×3 uint8)

    Returns:
        Tuple of:
          - binary:  Clean binary image (black walls on white BG, uint8)
          - gray:    Grayscale version (for OCR and other stages)
          - scale:   Resize scale factor applied (1.0 if no resize)
    """
    scale = 1.0

    # 1. Resize if too large
    h, w = image.shape[:2]
    max_dim = max(h, w)
    if max_dim > MAX_DIMENSION:
        scale = MAX_DIMENSION / max_dim
        new_w = int(w * scale)
        new_h = int(h * scale)
        image = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)

    # 2. Grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # 3. Gaussian blur — removes scanner noise and JPEG artifacts
    # Kernel size 3 is gentle; preserves thin lines
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)

    # 4. Adaptive thresholding
    # Converts to binary: pixels below threshold → black (0)
    # blockSize=15: local neighbourhood size for threshold calculation
    # C=10: constant subtracted from local mean (tune for floor plans)
    binary = cv2.adaptiveThreshold(
        blurred,
        maxValue=255,
        adaptiveMethod=cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        thresholdType=cv2.THRESH_BINARY,
        blockSize=15,
        C=10,
    )

    # 5. Invert if needed — we want walls as BLACK on WHITE background
    # Floor plans are typically black lines on white.
    # Check: if most pixels are dark, we have a dark-background image → invert.
    if np.mean(binary) < 127:
        binary = cv2.bitwise_not(binary)

    # 6. Deskew — correct scanning rotation (up to ±5°)
    binary = _deskew(binary)
    gray   = _deskew(gray, is_gray=True)

    return binary, gray, scale


def _deskew(image: np.ndarray, is_gray: bool = False) -> np.ndarray:
    """
    Correct slight rotation (deskewing) using the dominant line angle.

    Uses the Hough Lines transform to find the dominant angle in the
    image and rotates to correct it. Only corrects small angles (±10°)
    to avoid misidentifying intentional diagonal elements.

    Args:
        image:    Binary or grayscale image
        is_gray:  If True, fills background with 255 (white)

    Returns:
        Deskewed image (same size as input)
    """
    # Work with an inverted copy for edge detection
    if is_gray:
        edges = cv2.Canny(image, 50, 150)
    else:
        edges = cv2.bitwise_not(image)

    # Hough Lines to find dominant angles
    lines = cv2.HoughLinesP(
        edges,
        rho=1,
        theta=np.pi / 180,
        threshold=100,
        minLineLength=100,
        maxLineGap=10,
    )

    if lines is None:
        return image  # Cannot detect lines — return as-is

    # Collect angles of all detected lines
    angles = []
    for line in lines:
        x1, y1, x2, y2 = line[0]
        if x2 - x1 == 0:
            continue  # Skip vertical lines
        angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
        # Only use near-horizontal lines for deskew reference
        if abs(angle) < 10:
            angles.append(angle)

    if not angles:
        return image

    # Use median angle to avoid outliers
    median_angle = np.median(angles)

    # Only rotate if skew is meaningful (> 0.3°) but not extreme (< 10°)
    if abs(median_angle) < 0.3 or abs(median_angle) > 10:
        return image

    # Rotate the image to correct the skew
    h, w = image.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, median_angle, 1.0)
    fill_value = 255 if is_gray else 255
    rotated = cv2.warpAffine(
        image, M, (w, h),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=fill_value,
    )
    return rotated


def find_floor_plan_boundary(binary: np.ndarray) -> Tuple[int, int, int, int]:
    """
    Find the bounding box of the floor plan content within the image.

    Some scanned floor plans have borders, titles, or margins.
    This finds the main content area by finding the largest contour.

    Args:
        binary: Preprocessed binary image

    Returns:
        (x, y, w, h) bounding box of the main floor plan content
        Returns full image bounds if detection fails.
    """
    h, w = binary.shape[:2]

    # Invert: find dark regions (walls) as foreground
    inverted = cv2.bitwise_not(binary)

    # Find all contours
    contours, _ = cv2.findContours(
        inverted, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    if not contours:
        return 0, 0, w, h

    # Find the largest contour by area
    largest = max(contours, key=cv2.contourArea)
    area = cv2.contourArea(largest)

    # Must be at least 10% of the image to be meaningful
    if area < 0.1 * h * w:
        return 0, 0, w, h

    x, y, cw, ch = cv2.boundingRect(largest)
    return x, y, cw, ch

