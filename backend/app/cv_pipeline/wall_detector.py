# ============================================================
# cv_pipeline/wall_detector.py — Wall Line Detection
# ============================================================
# Stage 4 of the CV pipeline.
#
# Uses the Probabilistic Hough Line Transform to detect wall
# segments in the binary floor plan image.
#
# Returns a list of wall dictionaries matching the schema in
# schemas/detection.py (WallSegment).
# ============================================================

import cv2
import numpy as np
from typing import List, Dict, Any
import math


def detect_walls(binary: np.ndarray, min_line_length: int = 40) -> List[Dict[str, Any]]:
    """
    Detect wall segments using Probabilistic Hough Line Transform.

    The algorithm:
      1. Apply morphological operations to thicken and clean wall lines
      2. Edge detection (Canny)
      3. Hough Lines P — detects line segments directly
      4. Filter out very short lines (noise)
      5. Merge near-collinear duplicate lines
      6. Classify each line as horizontal/vertical/diagonal
      7. Estimate wall thickness from the binary image
      8. Assign confidence based on length and straightness

    Args:
        binary:          Preprocessed binary image (walls = black, BG = white)
        min_line_length: Minimum pixel length to keep a line (default 40 px)

    Returns:
        List of wall dicts: [{x1, y1, x2, y2, thickness, confidence}, ...]
    """
    h, w = binary.shape[:2]

    # --- Step 1: Morphological closing to connect broken wall lines ---
    # Creates a thicker version — helps detect walls drawn with thin lines
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    closed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=1)

    # --- Step 2: Invert and edge-detect ---
    inverted = cv2.bitwise_not(closed)
    edges = cv2.Canny(inverted, threshold1=50, threshold2=150, apertureSize=3)

    # --- Step 3: Probabilistic Hough Lines ---
    # Parameters tuned for architectural floor plans:
    #   rho=1: 1-pixel resolution
    #   theta=π/180: 1-degree resolution
    #   threshold=50: minimum votes for a line
    #   minLineLength: minimum segment length (passed in)
    #   maxLineGap=10: gap between segments to still join them
    lines = cv2.HoughLinesP(
        edges,
        rho=1,
        theta=np.pi / 180,
        threshold=50,
        minLineLength=min_line_length,
        maxLineGap=10,
    )

    if lines is None:
        return []

    # --- Step 4: Convert to list of wall dicts ---
    raw_walls = []
    for line in lines:
        x1, y1, x2, y2 = line[0]
        length = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
        if length < min_line_length:
            continue
        raw_walls.append({
            "x1": float(x1), "y1": float(y1),
            "x2": float(x2), "y2": float(y2),
            "length": length,
        })

    if not raw_walls:
        return []

    # --- Step 5: Merge near-duplicate lines ---
    merged = _merge_similar_lines(raw_walls)

    # --- Step 6: Estimate thickness and assign confidence ---
    walls = []
    for wall in merged:
        thickness = _estimate_thickness(binary, wall)
        confidence = _assign_confidence(wall["length"], thickness, h, w)
        walls.append({
            "x1": wall["x1"],
            "y1": wall["y1"],
            "x2": wall["x2"],
            "y2": wall["y2"],
            "thickness": thickness,
            "confidence": confidence,
        })

    return walls


def _merge_similar_lines(
    walls: List[Dict], angle_threshold: float = 5.0, distance_threshold: float = 15.0
) -> List[Dict]:
    """
    Merge near-duplicate wall segments.

    Two lines are considered duplicates if:
      - Their angles differ by < angle_threshold degrees
      - Their midpoints are within distance_threshold pixels

    When merging, the longest line is kept.
    """
    if not walls:
        return walls

    used = [False] * len(walls)
    merged = []

    for i, w1 in enumerate(walls):
        if used[i]:
            continue

        group = [w1]
        for j, w2 in enumerate(walls):
            if i == j or used[j]:
                continue
            if _lines_are_similar(w1, w2, angle_threshold, distance_threshold):
                group.append(w2)
                used[j] = True

        # Keep the longest wall from the group
        best = max(group, key=lambda x: x["length"])
        merged.append(best)
        used[i] = True

    return merged


def _lines_are_similar(
    w1: Dict, w2: Dict, angle_thr: float, dist_thr: float
) -> bool:
    """Check if two line segments are near-duplicates."""
    # Angle of each line (0–180 degrees)
    a1 = math.degrees(math.atan2(w1["y2"] - w1["y1"], w1["x2"] - w1["x1"])) % 180
    a2 = math.degrees(math.atan2(w2["y2"] - w2["y1"], w2["x2"] - w2["x1"])) % 180

    angle_diff = min(abs(a1 - a2), 180 - abs(a1 - a2))
    if angle_diff > angle_thr:
        return False

    # Midpoints
    mid1_x = (w1["x1"] + w1["x2"]) / 2
    mid1_y = (w1["y1"] + w1["y2"]) / 2
    mid2_x = (w2["x1"] + w2["x2"]) / 2
    mid2_y = (w2["y1"] + w2["y2"]) / 2

    dist = math.sqrt((mid1_x - mid2_x) ** 2 + (mid1_y - mid2_y) ** 2)
    return dist < dist_thr


def _estimate_thickness(binary: np.ndarray, wall: Dict, sample_points: int = 5) -> float:
    """
    Estimate the thickness of a wall by sampling perpendicular cross-sections.

    Samples several points along the wall, casts a perpendicular ray at each
    point, and measures the width of the dark region (the wall).
    Returns the median measured thickness, capped between 5 and 50 pixels.
    """
    h, w = binary.shape[:2]
    x1, y1, x2, y2 = wall["x1"], wall["y1"], wall["x2"], wall["y2"]

    dx = x2 - x1
    dy = y2 - y1
    length = math.sqrt(dx * dx + dy * dy)
    if length < 1:
        return 10.0

    # Unit perpendicular vector
    perp_x = -dy / length
    perp_y =  dx / length

    thicknesses = []
    for i in range(1, sample_points + 1):
        t = i / (sample_points + 1)
        cx = int(x1 + t * dx)
        cy = int(y1 + t * dy)

        # Scan along perpendicular — count dark pixels
        dark_count = 0
        for d in range(-30, 30):
            px = int(cx + d * perp_x)
            py = int(cy + d * perp_y)
            if 0 <= px < w and 0 <= py < h:
                if binary[py, px] < 128:  # Dark pixel = wall
                    dark_count += 1

        if dark_count > 0:
            thicknesses.append(float(dark_count))

    if not thicknesses:
        return 10.0

    thickness = float(np.median(thicknesses))
    return max(5.0, min(50.0, thickness))


def _assign_confidence(length: float, thickness: float, h: int, w: int) -> str:
    """
    Assign a confidence label based on line properties.

    High confidence:   long wall, typical thickness
    Medium confidence: medium length or unusual thickness
    Low confidence:    short or very thin/thick line
    """
    image_diag = math.sqrt(h * h + w * w)
    relative_length = length / image_diag

    if relative_length > 0.15 and 5 <= thickness <= 30:
        return "high"
    elif relative_length > 0.05 and 3 <= thickness <= 40:
        return "medium"
    else:
        return "low"

