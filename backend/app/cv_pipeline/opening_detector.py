# ============================================================
# cv_pipeline/opening_detector.py — Door & Window Detection
# ============================================================
# Stage 6 of the CV pipeline.
#
# Detects gaps in walls (doors) and window symbols.
#
# Door detection strategy:
#   - Find gaps in wall lines (short segments missing from walls)
#   - Look for door-arc shapes (quarter-circle arcs, typical in
#     architectural drawings)
#
# Window detection strategy:
#   - Detect parallel line pairs close to wall segments
#   - Detect the standard window symbol (line with parallel hatching)
# ============================================================

import cv2
import numpy as np
from typing import List, Dict, Any, Tuple
import math


def detect_openings(
    binary: np.ndarray,
    walls: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Detect doors and windows in the floor plan.

    Args:
        binary: Preprocessed binary image (walls = black, BG = white)
        walls:  List of wall segments from wall_detector (for context)

    Returns:
        Tuple of:
          - doors:   List of door dicts [{x, y, width, wall, confidence}, ...]
          - windows: List of window dicts [{x, y, width, wall, confidence}, ...]
    """
    doors   = _detect_doors(binary, walls)
    windows = _detect_windows(binary, walls)
    return doors, windows


# ------------------------------------------------------------------
# Door Detection
# ------------------------------------------------------------------

def _detect_doors(
    binary: np.ndarray, walls: List[Dict]
) -> List[Dict[str, Any]]:
    """
    Detect doors by looking for:
      1. Quarter-circle arcs (classic door-swing symbol)
      2. Gaps in wall lines
    """
    doors = []

    # Method 1: Circle/arc detection (door swing arcs)
    arc_doors = _detect_door_arcs(binary)
    doors.extend(arc_doors)

    # Method 2: Gap detection in walls
    gap_doors = _detect_wall_gaps(binary, walls)

    # Merge results — deduplicate doors that are close together
    all_doors = doors + gap_doors
    merged_doors = _deduplicate_openings(all_doors, threshold=40.0)

    return merged_doors


def _detect_door_arcs(binary: np.ndarray) -> List[Dict[str, Any]]:
    """
    Detect door-swing arcs using circle detection (HoughCircles).

    In standard architectural drawings, a door is shown as a line
    (the door panel) plus a quarter-circle arc (the swing path).
    The arc's radius equals the door width.
    """
    # Work on inverted image (arcs are dark lines on white)
    inverted = cv2.bitwise_not(binary)

    # Blur slightly to help circle detection
    blurred = cv2.GaussianBlur(inverted, (5, 5), 1)

    h, w = binary.shape[:2]
    min_dim = min(h, w)

    # Look for circles with radii in door-width range (20–150 px typically)
    circles = cv2.HoughCircles(
        blurred,
        cv2.HOUGH_GRADIENT,
        dp=1,                          # Accumulator resolution
        minDist=50,                    # Min distance between circle centres
        param1=50,                     # Canny upper threshold
        param2=25,                     # Accumulator threshold (lower = more detections)
        minRadius=max(20, min_dim // 50),
        maxRadius=min(150, min_dim // 5),
    )

    doors = []
    if circles is not None:
        circles = np.round(circles[0, :]).astype(int)
        for (cx, cy, r) in circles:
            # A door arc: the x,y is the hinge point, width = diameter
            doors.append({
                "x": float(cx),
                "y": float(cy),
                "width": float(r),   # radius = half door width
                "wall": None,
                "room_id": None,
                "confidence": "medium",
                "_source": "arc",
            })

    return doors


def _detect_wall_gaps(
    binary: np.ndarray, walls: List[Dict]
) -> List[Dict[str, Any]]:
    """
    Detect doors by finding gaps in wall segments.

    For each wall, check if there is a short gap (missing dark pixels)
    along its length. A gap of 60–120 pixels is typical door width.
    """
    if not walls:
        return []

    h, w = binary.shape[:2]
    doors = []

    for wall in walls:
        x1, y1, x2, y2 = wall["x1"], wall["y1"], wall["x2"], wall["y2"]
        length = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
        if length < 60:
            continue  # Too short to contain a door

        # Sample points along the wall
        num_samples = int(length)
        gap_start = None
        gap_pixels = 0

        for i in range(num_samples):
            t = i / num_samples
            px = int(x1 + t * (x2 - x1))
            py = int(y1 + t * (y2 - y1))
            if not (0 <= px < w and 0 <= py < h):
                continue

            # Check a small window around this point
            region = binary[
                max(0, py - 3): min(h, py + 4),
                max(0, px - 3): min(w, px + 4)
            ]
            is_dark = np.mean(region) < 200  # Mostly dark = wall present

            if not is_dark:
                # Entering a gap
                if gap_start is None:
                    gap_start = (px, py)
                gap_pixels += 1
            else:
                # Exiting a gap
                if gap_start is not None and 30 <= gap_pixels <= 150:
                    # Gap is in door-width range → record as door
                    gap_cx = (gap_start[0] + px) / 2
                    gap_cy = (gap_start[1] + py) / 2
                    doors.append({
                        "x": float(gap_cx),
                        "y": float(gap_cy),
                        "width": float(gap_pixels),
                        "wall": _wall_direction(wall),
                        "room_id": None,
                        "confidence": "high",
                        "_source": "gap",
                    })
                gap_start = None
                gap_pixels = 0

    return doors


# ------------------------------------------------------------------
# Window Detection
# ------------------------------------------------------------------

def _detect_windows(
    binary: np.ndarray, walls: List[Dict]
) -> List[Dict[str, Any]]:
    """
    Detect windows by looking for the standard window symbol:
    a gap in a wall with two parallel lines (the window frame).

    This is simpler than door detection — windows appear as
    short parallel lines set into a wall.
    """
    if not walls:
        return []

    h, w = binary.shape[:2]
    windows = []

    # Detect windows using a template-matching approach:
    # Look for regions along walls where there are pairs of parallel lines
    for wall in walls:
        x1, y1, x2, y2 = wall["x1"], wall["y1"], wall["x2"], wall["y2"]
        length = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
        if length < 40:
            continue

        # Perpendicular direction
        dx = (x2 - x1) / length
        dy = (y2 - y1) / length
        perp_x = -dy
        perp_y = dx

        # Sample along wall looking for window patterns
        step = 10
        window_start = None
        window_len = 0

        for i in range(0, int(length) - step, step):
            t = i / length
            cx = int(x1 + t * (x2 - x1))
            cy = int(y1 + t * (y2 - y1))

            # Sample perpendicular cross section
            has_parallel = _check_window_pattern(binary, cx, cy, perp_x, perp_y, h, w)

            if has_parallel:
                if window_start is None:
                    window_start = (cx, cy)
                window_len += step
            else:
                if window_start is not None and 30 <= window_len <= 200:
                    wx = (window_start[0] + cx) / 2
                    wy = (window_start[1] + cy) / 2
                    windows.append({
                        "x": float(wx),
                        "y": float(wy),
                        "width": float(window_len),
                        "wall": _wall_direction(wall),
                        "room_id": None,
                        "confidence": "medium",
                    })
                window_start = None
                window_len = 0

    return _deduplicate_openings(windows, threshold=50.0)


def _check_window_pattern(
    binary: np.ndarray,
    cx: int, cy: int,
    perp_x: float, perp_y: float,
    h: int, w: int,
    scan_range: int = 20,
) -> bool:
    """
    Check if a cross-section perpendicular to the wall shows a window pattern.
    A window pattern has two dark bands (frame lines) separated by a light gap.
    """
    profile = []
    for d in range(-scan_range, scan_range + 1):
        px = int(cx + d * perp_x)
        py = int(cy + d * perp_y)
        if 0 <= px < w and 0 <= py < h:
            profile.append(1 if binary[py, px] < 128 else 0)
        else:
            profile.append(0)

    if len(profile) < 10:
        return False

    # Count dark-light-dark transitions (window frame pattern)
    transitions = 0
    for i in range(1, len(profile)):
        if profile[i] != profile[i - 1]:
            transitions += 1

    # A window cross-section typically has 4 transitions (D→L→D→L→D or similar)
    return transitions >= 3


# ------------------------------------------------------------------
# Utilities
# ------------------------------------------------------------------

def _wall_direction(wall: Dict) -> str:
    """Classify a wall as 'horizontal' or 'vertical' or 'diagonal'."""
    dx = abs(wall["x2"] - wall["x1"])
    dy = abs(wall["y2"] - wall["y1"])
    if dy == 0 or (dx > 0 and dx / (dy + 1) > 2):
        return "horizontal"
    elif dx == 0 or (dy > 0 and dy / (dx + 1) > 2):
        return "vertical"
    return "diagonal"


def _deduplicate_openings(
    openings: List[Dict], threshold: float = 40.0
) -> List[Dict]:
    """
    Remove duplicate door/window detections that are very close together.
    Keeps the one with the highest confidence.
    """
    if not openings:
        return openings

    conf_order = {"high": 3, "medium": 2, "low": 1}
    # Sort by confidence descending
    openings = sorted(openings, key=lambda o: conf_order.get(o.get("confidence", "low"), 1), reverse=True)

    kept = []
    for o in openings:
        is_dup = False
        for k in kept:
            dist = math.sqrt((o["x"] - k["x"]) ** 2 + (o["y"] - k["y"]) ** 2)
            if dist < threshold:
                is_dup = True
                break
        if not is_dup:
            # Remove internal _source key before returning
            o.pop("_source", None)
            kept.append(o)

    return kept

