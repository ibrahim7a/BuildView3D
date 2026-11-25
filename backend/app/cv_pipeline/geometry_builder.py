# ============================================================
# cv_pipeline/geometry_builder.py — Structured JSON Builder
# ============================================================
# Stage 9 (final) of the CV pipeline.
#
# Takes all the raw detections from previous stages and assembles
# them into the final structured JSON that:
#   - Matches the DetectionResult schema (schemas/detection.py)
#   - Is ready to be stored in the database
#   - Is consumed by the 3D generator (Phase 5)
#
# Also:
#   - Associates doors/windows with the nearest room
#   - Applies scale factor to compute real-world dimensions
#   - Generates overall confidence score
#   - Produces flags for uncertain detections
# ============================================================

import math
from typing import List, Dict, Any, Optional


def build_geometry(
    walls: List[Dict],
    rooms: List[Dict],
    doors: List[Dict],
    windows: List[Dict],
    staircases: List[Dict],
    dimensions: List[Dict],
    flags: List[Dict],
    image_width_px: int,
    image_height_px: int,
    scale_factor: float,
) -> Dict[str, Any]:
    """
    Assemble all CV stage outputs into the final detection result dict.

    Args:
        walls, rooms, doors, windows, staircases: Outputs from detector stages
        dimensions:   Dimension measurements from OCR
        flags:        Warning flags accumulated during processing
        image_width_px, image_height_px: Processed image dimensions
        scale_factor: Metres per pixel (detected or default)

    Returns:
        A dict matching DetectionResultResponse schema, ready for DB storage.
    """
    # Apply scale factor to refine room areas from pixel measurements
    rooms = _apply_scale_to_rooms(rooms, scale_factor)

    # Associate doors and windows with rooms
    doors   = _associate_with_rooms(doors,   rooms)
    windows = _associate_with_rooms(windows, rooms)

    # Apply OCR dimension data to refine scale factor estimate
    refined_scale = _refine_scale_from_dimensions(dimensions, walls, scale_factor)

    # Collect additional flags for low-confidence items
    flags = flags + _generate_flags(rooms, walls, doors, refined_scale)

    # Compute overall confidence
    overall_confidence = _compute_overall_confidence(walls, rooms, doors, windows)

    return {
        "walls":        walls,
        "rooms":        rooms,
        "doors":        doors,
        "windows":      windows,
        "staircases":   staircases,
        "flags":        flags,
        "scale_factor": refined_scale,
        "image_width_px":  image_width_px,
        "image_height_px": image_height_px,
        "overall_confidence": overall_confidence,
    }


def _apply_scale_to_rooms(rooms: List[Dict], scale_factor: float) -> List[Dict]:
    """Recalculate room areas using the confirmed scale factor."""
    for room in rooms:
        poly = room.get("polygon", [])
        if poly:
            # Shoelace formula for polygon area
            n = len(poly)
            area_px = 0.0
            for i in range(n):
                j = (i + 1) % n
                area_px += poly[i][0] * poly[j][1]
                area_px -= poly[j][0] * poly[i][1]
            area_px = abs(area_px) / 2.0
            room["area_sqm"] = round(area_px * (scale_factor ** 2), 1)
    return rooms


def _associate_with_rooms(
    openings: List[Dict], rooms: List[Dict]
) -> List[Dict]:
    """
    Assign each door/window to the nearest room by centroid distance.

    Sets the 'room_id' field on each opening.
    """
    if not rooms or not openings:
        return openings

    # Compute room centroids
    centroids = []
    for room in rooms:
        poly = room.get("polygon", [])
        if poly:
            cx = sum(p[0] for p in poly) / len(poly)
            cy = sum(p[1] for p in poly) / len(poly)
        else:
            cx, cy = 0.0, 0.0
        centroids.append((cx, cy, room["id"]))

    for opening in openings:
        ox, oy = opening.get("x", 0), opening.get("y", 0)
        best_room_id = None
        best_dist = float("inf")

        for cx, cy, room_id in centroids:
            dist = math.sqrt((ox - cx) ** 2 + (oy - cy) ** 2)
            if dist < best_dist:
                best_dist = dist
                best_room_id = room_id

        # Only assign if reasonably close (within 300 px)
        if best_dist < 300:
            opening["room_id"] = best_room_id

    return openings


def _refine_scale_from_dimensions(
    dimensions: List[Dict],
    walls: List[Dict],
    default_scale: float,
) -> float:
    """
    Try to refine the scale factor using OCR-extracted dimension values.

    If OCR found dimension labels near wall segments, we can estimate
    the scale as: scale = known_length_metres / wall_length_pixels

    Returns the refined scale, or the default if OCR data is insufficient.
    """
    if not dimensions or not walls:
        return default_scale

    # For each OCR dimension, find the nearest wall segment
    refined_scales = []

    for dim in dimensions:
        dim_x, dim_y = dim["x"], dim["y"]
        value_m = dim["value_metres"]

        if value_m <= 0:
            continue

        # Find nearest wall
        best_wall = None
        best_dist = float("inf")
        for wall in walls:
            mid_x = (wall["x1"] + wall["x2"]) / 2
            mid_y = (wall["y1"] + wall["y2"]) / 2
            dist = math.sqrt((dim_x - mid_x) ** 2 + (dim_y - mid_y) ** 2)
            if dist < best_dist:
                best_dist = dist
                best_wall = wall

        if best_wall and best_dist < 100:
            wall_len_px = math.sqrt(
                (best_wall["x2"] - best_wall["x1"]) ** 2 +
                (best_wall["y2"] - best_wall["y1"]) ** 2
            )
            if wall_len_px > 10:
                scale = value_m / wall_len_px
                if 0.001 <= scale <= 1.0:  # Sanity check
                    refined_scales.append(scale)

    if not refined_scales:
        return default_scale

    import statistics
    # Use median to reject outliers
    return round(statistics.median(refined_scales), 5)


def _generate_flags(
    rooms: List[Dict],
    walls: List[Dict],
    doors: List[Dict],
    scale_factor: float,
) -> List[Dict]:
    """
    Generate warning flags for uncertain detections.

    Flags are shown to the user in the correction interface so
    they can verify or fix the detection before 3D generation.
    """
    flags = []

    # Flag if no rooms detected
    if not rooms:
        flags.append({
            "type": "no_rooms_detected",
            "message": "No enclosed room areas were detected. "
                       "The floor plan may have open walls or be unclear. "
                       "Please verify the floor plan image quality.",
        })

    # Flag rooms with low confidence labels
    for room in rooms:
        if room.get("confidence") == "low":
            flags.append({
                "type": "low_confidence_room",
                "room_id": room["id"],
                "message": f"Room label '{room['label']}' was estimated from area only. "
                           f"Please verify this is correct.",
            })

    # Flag if very few walls detected
    if len(walls) < 4:
        flags.append({
            "type": "few_walls_detected",
            "message": f"Only {len(walls)} wall segments detected. "
                       "The image may be low quality or not a standard floor plan.",
        })

    # Flag if scale factor is the default (not extracted from image)
    if scale_factor == 0.05:
        flags.append({
            "type": "default_scale_used",
            "message": "Scale was not detected from the floor plan. "
                       "A default scale of 1px = 5cm was used. "
                       "Please enter a known room dimension to calibrate.",
        })

    # Flag rooms with unrealistic areas
    for room in rooms:
        area = room.get("area_sqm", 0)
        if area < 1.0:
            flags.append({
                "type": "small_room",
                "room_id": room["id"],
                "message": f"Room '{room['label']}' has an unusually small area ({area} m²). "
                           "This may be a detection error.",
            })
        elif area > 200:
            flags.append({
                "type": "large_room",
                "room_id": room["id"],
                "message": f"Room '{room['label']}' has an unusually large area ({area} m²). "
                           "Please verify the scale factor.",
            })

    return flags


def _compute_overall_confidence(
    walls: List[Dict],
    rooms: List[Dict],
    doors: List[Dict],
    windows: List[Dict],
) -> float:
    """
    Compute an overall confidence score for the detection (0.0 → 1.0).

    Score components:
      - Wall count and confidence
      - Room count and confidence
      - Presence of doors/windows
    """
    scores = []

    # Wall score
    if walls:
        high_walls = sum(1 for w in walls if w.get("confidence") == "high")
        wall_conf = high_walls / len(walls)
        # More walls = more complex floor plan = more chance for errors
        wall_count_score = min(1.0, len(walls) / 20)
        scores.append((wall_conf + wall_count_score) / 2)
    else:
        scores.append(0.0)

    # Room score
    if rooms:
        high_rooms = sum(1 for r in rooms if r.get("confidence") in ("high", "medium"))
        room_conf = high_rooms / len(rooms)
        scores.append(room_conf)
    else:
        scores.append(0.0)

    # Opening score (bonus if doors/windows found — indicates good detection)
    has_openings = (len(doors) + len(windows)) > 0
    scores.append(0.6 if has_openings else 0.3)

    return round(sum(scores) / len(scores), 2)

