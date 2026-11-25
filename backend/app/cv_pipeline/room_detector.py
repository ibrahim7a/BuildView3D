# ============================================================
# cv_pipeline/room_detector.py — Room Area Detection
# ============================================================
# Stage 5 of the CV pipeline.
#
# Finds enclosed regions (rooms) in the floor plan using a
# flood-fill approach on the binary image.
#
# Strategy:
#   1. Dilate wall lines slightly to ensure closed boundaries
#   2. Find all enclosed regions using contour detection
#   3. Filter by area (too small = noise, too large = whole image)
#   4. Compute polygon, bounding box, and estimated area in sq metres
#   5. Assign preliminary room labels based on area heuristics
# ============================================================

import cv2
import numpy as np
from typing import List, Dict, Any, Tuple


# Area heuristics for room classification (in square metres)
# These are typical ranges — users can correct them in Phase 4
ROOM_SIZE_HEURISTICS = [
    ("Bathroom",    0.0,   8.0),
    ("Kitchen",     5.0,  20.0),
    ("Bedroom",    10.0,  30.0),
    ("Living Room", 15.0,  60.0),
    ("Dining Room", 10.0,  35.0),
    ("Hallway",     2.0,  15.0),
    ("Garage",     15.0,  60.0),
]

# Minimum room area in pixels (removes very small noise regions)
MIN_ROOM_AREA_PX = 1500

# Maximum room fraction of image (rooms shouldn't be the entire image)
MAX_ROOM_FRACTION = 0.70


def detect_rooms(
    binary: np.ndarray,
    scale_factor: float = 0.05,
) -> List[Dict[str, Any]]:
    """
    Detect enclosed room regions in a binary floor plan image.

    Args:
        binary:       Preprocessed binary image (walls = black, BG = white)
        scale_factor: Metres per pixel. Used to calculate real-world area.
                      Default 0.05 m/px = 20 px per metre.

    Returns:
        List of room dicts: [{id, label, confidence, polygon, area_sqm}, ...]
    """
    h, w = binary.shape[:2]
    total_area = h * w

    # --- Step 1: Dilate walls to close small gaps ---
    # This ensures flood-fill doesn't leak through thin gaps between walls.
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    dilated = cv2.dilate(cv2.bitwise_not(binary), kernel, iterations=2)
    closed_walls = cv2.bitwise_not(dilated)

    # --- Step 2: Find enclosed regions ---
    # Invert: enclosed white regions become foreground for contour finding
    inverted = cv2.bitwise_not(closed_walls)

    contours, hierarchy = cv2.findContours(
        inverted,
        cv2.RETR_CCOMP,          # Retrieves all contours with 2-level hierarchy
        cv2.CHAIN_APPROX_SIMPLE, # Compress horizontal/vertical/diagonal segments
    )

    if contours is None or len(contours) == 0:
        return []

    # --- Step 3: Filter and process contours ---
    rooms = []
    room_counter = 0

    for idx, contour in enumerate(contours):
        area_px = cv2.contourArea(contour)

        # Skip noise and the whole-image outline
        if area_px < MIN_ROOM_AREA_PX:
            continue
        if area_px > MAX_ROOM_FRACTION * total_area:
            continue

        # Only keep "hole" contours (interior enclosed regions)
        # In RETR_CCOMP: hierarchy[0][idx][3] >= 0 means it has a parent
        if hierarchy is not None and hierarchy[0][idx][3] < 0:
            continue

        # Simplify contour polygon (reduce point count while keeping shape)
        epsilon = 0.02 * cv2.arcLength(contour, closed=True)
        approx = cv2.approxPolyDP(contour, epsilon, closed=True)

        # Must have at least 3 points to be a polygon
        if len(approx) < 3:
            continue

        # Convert to list of [x, y] pairs
        polygon = [[float(pt[0][0]), float(pt[0][1])] for pt in approx]

        # Real-world area in square metres
        area_sqm = area_px * (scale_factor ** 2)

        # Classify room type by area
        label, confidence = _classify_room(area_sqm)

        room_counter += 1
        rooms.append({
            "id": f"room_{room_counter}",
            "label": label,
            "confidence": confidence,
            "polygon": polygon,
            "area_sqm": round(area_sqm, 1),
            "detected_label": None,  # Will be filled by OCR stage
        })

    # Sort rooms by area descending (largest room first)
    rooms.sort(key=lambda r: r["area_sqm"], reverse=True)

    # Re-assign IDs in sorted order
    for i, room in enumerate(rooms, start=1):
        room["id"] = f"room_{i}"

    return rooms


def _classify_room(area_sqm: float) -> Tuple[str, str]:
    """
    Classify a room by its area in square metres.

    Returns:
        (label, confidence) tuple
        confidence is "medium" because area alone is not definitive —
        users confirm in the correction interface.
    """
    # Find all matching categories
    matches = [
        label for label, min_a, max_a in ROOM_SIZE_HEURISTICS
        if min_a <= area_sqm <= max_a
    ]

    if not matches:
        # Very large → probably living area; very small → utility
        label = "Large Room" if area_sqm > 60 else "Small Room"
        return label, "low"

    if len(matches) == 1:
        return matches[0], "medium"

    # Multiple matches → pick the most specific one
    # Priority order (from most distinctive area to least)
    priority = ["Bathroom", "Kitchen", "Hallway", "Dining Room",
                "Bedroom", "Garage", "Living Room"]
    for p in priority:
        if p in matches:
            return p, "low"  # Multiple matches = lower confidence

    return matches[0], "low"


def get_room_centres(rooms: List[Dict]) -> List[Tuple[float, float]]:
    """
    Compute the geometric centre of each room polygon.

    Args:
        rooms: List of room dicts (each with 'polygon' key)

    Returns:
        List of (cx, cy) tuples, one per room
    """
    centres = []
    for room in rooms:
        poly = room.get("polygon", [])
        if not poly:
            centres.append((0.0, 0.0))
            continue
        cx = sum(pt[0] for pt in poly) / len(poly)
        cy = sum(pt[1] for pt in poly) / len(poly)
        centres.append((cx, cy))
    return centres

