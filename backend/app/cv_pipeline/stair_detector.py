# ============================================================
# cv_pipeline/stair_detector.py — Staircase Detection
# ============================================================
# Stage 8 of the CV pipeline.
#
# Detects staircase patterns in floor plans.
#
# In architectural drawings, staircases appear as a series of
# parallel lines (the stair steps) grouped closely together,
# often with an arrow indicating direction.
#
# Strategy:
#   - Find groups of parallel lines that are evenly spaced
#   - A group of 3+ evenly-spaced parallel lines = staircase candidate
# ============================================================

import cv2
import numpy as np
from typing import List, Dict, Any
import math


def detect_staircases(binary: np.ndarray) -> List[Dict[str, Any]]:
    """
    Detect staircase patterns in a floor plan image.

    Args:
        binary: Preprocessed binary image (walls = black, BG = white)

    Returns:
        List of staircase dicts:
        [{x, y, width, height, step_count, confidence}, ...]
    """
    h, w = binary.shape[:2]

    # Detect all line segments
    inverted = cv2.bitwise_not(binary)
    edges    = cv2.Canny(inverted, 30, 100)

    lines = cv2.HoughLinesP(
        edges,
        rho=1,
        theta=np.pi / 180,
        threshold=30,
        minLineLength=20,
        maxLineGap=5,
    )

    if lines is None:
        return []

    # Separate into horizontal and vertical line groups
    horizontal = []
    vertical   = []

    for line in lines:
        x1, y1, x2, y2 = line[0]
        angle = abs(math.degrees(math.atan2(y2 - y1, x2 - x1)))

        if angle < 20 or angle > 160:  # Near-horizontal
            horizontal.append((x1, y1, x2, y2))
        elif 70 < angle < 110:          # Near-vertical
            vertical.append((x1, y1, x2, y2))

    staircases = []

    # Look for evenly-spaced horizontal groups
    h_stairs = _find_stair_groups(horizontal, axis="horizontal")
    staircases.extend(h_stairs)

    # Look for evenly-spaced vertical groups
    v_stairs = _find_stair_groups(vertical, axis="vertical")
    staircases.extend(v_stairs)

    return staircases


def _find_stair_groups(
    lines: List[tuple], axis: str, min_steps: int = 3, max_spacing_variance: float = 0.4
) -> List[Dict[str, Any]]:
    """
    Find groups of evenly-spaced parallel lines (staircase steps).

    Args:
        lines:                List of (x1,y1,x2,y2) tuples
        axis:                 "horizontal" or "vertical"
        min_steps:            Minimum number of parallel lines to be a staircase
        max_spacing_variance: Maximum coefficient of variation for spacing

    Returns:
        List of staircase dicts
    """
    if len(lines) < min_steps:
        return []

    # Sort by perpendicular position (y for horizontal, x for vertical)
    if axis == "horizontal":
        lines = sorted(lines, key=lambda l: (l[1] + l[3]) / 2)
        positions = [(l[1] + l[3]) / 2 for l in lines]
    else:
        lines = sorted(lines, key=lambda l: (l[0] + l[2]) / 2)
        positions = [(l[0] + l[2]) / 2 for l in lines]

    # Sliding window to find groups with consistent spacing
    staircases = []
    n = len(lines)

    i = 0
    while i < n - min_steps + 1:
        # Try to build a group starting at i
        group = [i]
        base_spacing = positions[i + 1] - positions[i] if i + 1 < n else None

        if base_spacing is None or base_spacing < 3 or base_spacing > 50:
            i += 1
            continue

        for j in range(i + 1, min(i + 20, n)):
            spacing = positions[j] - positions[j - 1]
            # Check if this spacing is consistent with the base
            if base_spacing > 0:
                rel_diff = abs(spacing - base_spacing) / base_spacing
                if rel_diff <= max_spacing_variance:
                    group.append(j)
                else:
                    break

        if len(group) >= min_steps:
            # Extract bounding box of this stair group
            group_lines = [lines[idx] for idx in group]

            all_x = [pt for l in group_lines for pt in [l[0], l[2]]]
            all_y = [pt for l in group_lines for pt in [l[1], l[3]]]

            x_min, x_max = min(all_x), max(all_x)
            y_min, y_max = min(all_y), max(all_y)

            staircases.append({
                "x": float(x_min),
                "y": float(y_min),
                "width": float(x_max - x_min),
                "height": float(y_max - y_min),
                "step_count": len(group),
                "confidence": "medium" if len(group) >= 5 else "low",
            })
            i += len(group)  # Skip past this group
        else:
            i += 1

    return staircases

