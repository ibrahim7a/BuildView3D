# ============================================================
# cv_pipeline/orchestrator.py — Main CV Pipeline Runner
# ============================================================
# This module ties together all the individual CV stages into
# one clean function: run_pipeline(image_path) → dict
#
# Stage order:
#   1. Load image
#   2. Preprocess (grayscale, resize, threshold, deskew)
#   3. Detect walls (Hough Lines P)
#   4. Detect rooms (contour flood-fill)
#   5. Detect openings (doors + windows)
#   6. OCR (optional — dimension labels + room text)
#   7. Detect staircases (parallel line groups)
#   8. Build final geometry JSON
# ============================================================

import cv2
import numpy as np
from pathlib import Path

from app.cv_pipeline.preprocessor import preprocess
from app.cv_pipeline.wall_detector import detect_walls
from app.cv_pipeline.room_detector import detect_rooms
from app.cv_pipeline.opening_detector import detect_openings
from app.cv_pipeline.stair_detector import detect_staircases
from app.cv_pipeline.ocr_extractor import extract_text, assign_ocr_labels_to_rooms
from app.cv_pipeline.geometry_builder import build_geometry

# ----------------------------------------------------------
# Default scale: 1 pixel = 5 cm (used if OCR can't detect it)
# ----------------------------------------------------------
DEFAULT_SCALE = 0.05  # meters per pixel


def run_pipeline(image_path: str) -> dict:
    """
    Run the full CV pipeline on a floor plan image file.

    Args:
        image_path: Absolute path to the image (JPG / PNG / BMP).
                    PDF files should be converted to PNG first.

    Returns:
        A dict matching the DetectionResult schema with keys:
        walls, rooms, doors, windows, staircases, dimensions,
        flags, overall_confidence, scale_factor,
        image_width_px, image_height_px.

    Raises:
        RuntimeError: If the image cannot be loaded or any
                      stage throws an unexpected error.
    """

    # ----------------------------------------------------------
    # Step 1: Load the image from disk
    # ----------------------------------------------------------
    image_path = str(image_path)  # accept Path objects too
    image = cv2.imread(image_path)
    if image is None:
        raise RuntimeError(
            f"Could not load image: {image_path}. "
            "Make sure the file exists and is a valid image (JPG/PNG/BMP)."
        )

    h_orig, w_orig = image.shape[:2]
    print(f"[Pipeline] Loaded image: {w_orig}×{h_orig} px")

    # ----------------------------------------------------------
    # Step 2: Preprocess
    # Returns: binary (thresholded B&W), gray, resize_scale
    # ----------------------------------------------------------
    try:
        binary, gray, resize_scale = preprocess(image)
        h_proc, w_proc = binary.shape[:2]
        print(f"[Pipeline] Preprocessed: {w_proc}×{h_proc} px (scale={resize_scale:.3f})")
    except Exception as exc:
        raise RuntimeError(f"Preprocessing failed: {exc}") from exc

    # ----------------------------------------------------------
    # Step 3: Detect walls
    # Returns: list of WallSegment-compatible dicts
    # ----------------------------------------------------------
    walls = []
    try:
        walls = detect_walls(binary, min_line_length=40)
        print(f"[Pipeline] Detected {len(walls)} walls")
    except Exception as exc:
        print(f"[Pipeline] ⚠ Wall detection error: {exc}")

    # ----------------------------------------------------------
    # Step 4: Detect rooms
    # Returns: list of RoomPolygon-compatible dicts
    # ----------------------------------------------------------
    rooms = []
    try:
        rooms = detect_rooms(binary, scale_factor=DEFAULT_SCALE)
        print(f"[Pipeline] Detected {len(rooms)} rooms")
    except Exception as exc:
        print(f"[Pipeline] ⚠ Room detection error: {exc}")

    # ----------------------------------------------------------
    # Step 5: Detect openings (doors + windows)
    # Returns: (doors_list, windows_list)
    # ----------------------------------------------------------
    doors, windows = [], []
    try:
        doors, windows = detect_openings(binary, walls)
        print(f"[Pipeline] Detected {len(doors)} doors, {len(windows)} windows")
    except Exception as exc:
        print(f"[Pipeline] ⚠ Opening detection error: {exc}")

    # ----------------------------------------------------------
    # Step 6: OCR — extract dimension labels + room text
    # Returns: (dimensions_list, room_texts_list, ocr_flags_list)
    # ocr_extractor handles missing Tesseract gracefully
    # ----------------------------------------------------------
    dimensions, room_texts, ocr_flags = [], [], []
    try:
        dimensions, room_texts, ocr_flags = extract_text(gray)
        print(f"[Pipeline] OCR: {len(dimensions)} dimensions, {len(room_texts)} room labels")
    except Exception as exc:
        print(f"[Pipeline] ⚠ OCR error (non-fatal): {exc}")
        ocr_flags = [{"type": "OCR_ERROR", "message": str(exc)}]

    # ----------------------------------------------------------
    # Step 7: Detect staircases
    # Returns: list of Staircase-compatible dicts
    # ----------------------------------------------------------
    staircases = []
    try:
        staircases = detect_staircases(binary)
        print(f"[Pipeline] Detected {len(staircases)} staircases")
    except Exception as exc:
        print(f"[Pipeline] ⚠ Staircase detection error: {exc}")

    # ----------------------------------------------------------
    # Step 8: Assign OCR room labels to detected rooms (if any)
    # ----------------------------------------------------------
    if room_texts and rooms:
        try:
            rooms = assign_ocr_labels_to_rooms(rooms, room_texts)
        except Exception as exc:
            print(f"[Pipeline] ⚠ OCR label assignment error: {exc}")

    # ----------------------------------------------------------
    # Step 9: Build final geometry JSON
    # Returns: the full detection dict
    # ----------------------------------------------------------
    try:
        result = build_geometry(
            walls=walls,
            rooms=rooms,
            doors=doors,
            windows=windows,
            staircases=staircases,
            dimensions=dimensions,
            flags=ocr_flags,
            image_width_px=w_proc,
            image_height_px=h_proc,
            scale_factor=DEFAULT_SCALE,
        )
    except Exception as exc:
        raise RuntimeError(f"Geometry building failed: {exc}") from exc

    print(
        f"[Pipeline] ✅ Done — confidence={result.get('overall_confidence', 0):.2f}, "
        f"flags={len(result.get('flags', []))}"
    )
    return result
