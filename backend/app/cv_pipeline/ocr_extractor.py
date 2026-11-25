# ============================================================
# cv_pipeline/ocr_extractor.py — OCR Dimension Extraction
# ============================================================
# Stage 7 of the CV pipeline.
#
# Reads dimension labels and room name text from the floor plan
# image using Tesseract OCR.
#
# Two tasks:
#   1. Extract dimension values (e.g. "3.5m", "12ft", "4500mm")
#      and return them as (value_metres, x, y) tuples
#
#   2. Extract room name text (e.g. "BEDROOM", "LIVING ROOM")
#      to improve room label accuracy beyond the area heuristic
#
# Tesseract is optional — if not installed, this stage is skipped
# and a flag is added to inform the user.
# ============================================================

import re
import math
from typing import List, Dict, Any, Optional, Tuple
import numpy as np


# Regex patterns for dimension detection
# Matches: "3.5m", "3.5 m", "12ft", "4500mm", "4500 mm", "10'6\""
_DIM_PATTERNS = [
    # Metres: 3.5m, 3.5 m, 3500mm
    (r"(\d+\.?\d*)\s*mm", lambda m: float(m) / 1000),
    (r"(\d+\.?\d*)\s*m\b", lambda m: float(m)),
    (r"(\d+\.?\d*)\s*cm", lambda m: float(m) / 100),
    # Feet & inches: 12ft, 10'6"
    (r"(\d+)\s*ft\b", lambda m: float(m) * 0.3048),
    (r"(\d+)\s*'\s*(\d+)\s*\"", None),  # feet'inches" — handled separately
    (r"(\d+\.?\d*)\s*'", lambda m: float(m) * 0.3048),
]

# Common room name keywords in floor plans (uppercase)
_ROOM_KEYWORDS = [
    "BEDROOM", "BED", "BED ROOM",
    "BATHROOM", "BATH", "WC", "TOILET", "SHOWER",
    "KITCHEN", "KIT",
    "LIVING", "LOUNGE", "SITTING",
    "DINING", "DINE",
    "HALLWAY", "HALL", "ENTRY", "ENTRANCE", "FOYER",
    "GARAGE", "CAR",
    "LAUNDRY", "UTILITY",
    "OFFICE", "STUDY",
    "STAIRS", "STAIR",
    "BALCONY", "TERRACE", "PATIO",
    "STORE", "STORAGE", "LINEN",
    "MASTER",
]


def extract_text(
    gray_image: np.ndarray,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict]]:
    """
    Extract dimension labels and room names from a grayscale floor plan.

    Args:
        gray_image:  Grayscale image (from preprocessor)

    Returns:
        Tuple of:
          - dimensions: [{value_metres, x, y, raw_text}, ...]
          - room_texts: [{text, x, y, matched_label}, ...]
          - flags:      [{type, message}, ...] — warns if OCR unavailable
    """
    flags = []

    # Try to import pytesseract
    try:
        import pytesseract
        from PIL import Image as PILImage

        # Check if Tesseract binary is available
        try:
            pytesseract.get_tesseract_version()
        except Exception:
            flags.append({
                "type": "ocr_unavailable",
                "message": (
                    "Tesseract OCR is not installed or not found in PATH. "
                    "Room labels and dimension extraction are unavailable. "
                    "Install Tesseract from: https://github.com/UB-Mannheim/tesseract/wiki"
                ),
            })
            return [], [], flags

        dimensions, room_texts = _run_ocr(gray_image, pytesseract, PILImage)
        return dimensions, room_texts, flags

    except ImportError:
        flags.append({
            "type": "ocr_unavailable",
            "message": (
                "pytesseract is not installed. "
                "Run: pip install pytesseract  to enable dimension extraction."
            ),
        })
        return [], [], flags


def _run_ocr(
    gray_image: np.ndarray, pytesseract, PILImage
) -> Tuple[List[Dict], List[Dict]]:
    """
    Run Tesseract OCR and extract dimensions and room names.
    """
    import cv2

    # Upscale the image for better OCR accuracy (Tesseract works best at 300 DPI)
    h, w = gray_image.shape[:2]
    scale = max(1.0, 2000.0 / max(h, w))
    if scale > 1.0:
        upscaled = cv2.resize(
            gray_image,
            (int(w * scale), int(h * scale)),
            interpolation=cv2.INTER_CUBIC,
        )
    else:
        upscaled = gray_image.copy()
        scale = 1.0

    # Apply threshold for cleaner OCR
    _, thresh = cv2.threshold(upscaled, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # Convert to PIL Image for pytesseract
    pil_image = PILImage.fromarray(thresh)

    # OCR with word bounding boxes
    # config: psm 11 = sparse text (best for floor plans with scattered text)
    custom_config = r"--psm 11 --oem 3"

    try:
        data = pytesseract.image_to_data(
            pil_image,
            config=custom_config,
            output_type=pytesseract.Output.DICT,
        )
    except Exception:
        return [], []

    dimensions = []
    room_texts = []

    for i, text in enumerate(data["text"]):
        text = str(text).strip()
        if not text or data["conf"][i] < 20:
            continue  # Skip low-confidence and empty results

        # Scale bounding box back to original image coordinates
        x = data["left"][i] / scale
        y = data["top"][i] / scale
        bw = data["width"][i] / scale
        bh = data["height"][i] / scale
        cx = x + bw / 2
        cy = y + bh / 2

        # Try to parse as a dimension
        dim = _parse_dimension(text)
        if dim is not None:
            dimensions.append({
                "value_metres": dim,
                "x": float(cx),
                "y": float(cy),
                "raw_text": text,
            })
            continue

        # Try to match as a room label
        room_match = _match_room_keyword(text.upper())
        if room_match:
            room_texts.append({
                "text": text,
                "x": float(cx),
                "y": float(cy),
                "matched_label": room_match,
            })

    return dimensions, room_texts


def _parse_dimension(text: str) -> Optional[float]:
    """
    Parse a text string as a physical dimension in metres.

    Returns metres as a float, or None if not a dimension.
    """
    text = text.strip()

    # Feet + inches: e.g. "10'6\""
    feet_inches = re.search(r"(\d+)'\s*(\d+)\"", text)
    if feet_inches:
        feet   = int(feet_inches.group(1))
        inches = int(feet_inches.group(2))
        return (feet * 12 + inches) * 0.0254

    for pattern, converter in _DIM_PATTERNS:
        if converter is None:
            continue
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            try:
                val = converter(m.group(1))
                # Sanity check: dimensions should be between 0.1m and 100m
                if 0.1 <= val <= 100:
                    return round(val, 3)
            except (ValueError, IndexError):
                continue

    return None


def _match_room_keyword(text_upper: str) -> Optional[str]:
    """
    Match OCR text against known room name keywords.

    Returns a canonical room label (e.g. "Bedroom") or None.
    """
    keyword_to_label = {
        "BEDROOM": "Bedroom", "BED": "Bedroom", "BED ROOM": "Bedroom",
        "MASTER": "Master Bedroom",
        "BATHROOM": "Bathroom", "BATH": "Bathroom",
        "WC": "Bathroom", "TOILET": "Bathroom", "SHOWER": "Bathroom",
        "KITCHEN": "Kitchen", "KIT": "Kitchen",
        "LIVING": "Living Room", "LOUNGE": "Living Room", "SITTING": "Living Room",
        "DINING": "Dining Room", "DINE": "Dining Room",
        "HALLWAY": "Hallway", "HALL": "Hallway",
        "ENTRY": "Hallway", "ENTRANCE": "Hallway", "FOYER": "Hallway",
        "GARAGE": "Garage", "CAR": "Garage",
        "LAUNDRY": "Laundry", "UTILITY": "Utility",
        "OFFICE": "Office", "STUDY": "Office",
        "STAIRS": "Staircase", "STAIR": "Staircase",
        "BALCONY": "Balcony", "TERRACE": "Balcony", "PATIO": "Balcony",
        "STORE": "Storage", "STORAGE": "Storage", "LINEN": "Storage",
    }

    for keyword, label in keyword_to_label.items():
        if keyword in text_upper:
            return label

    return None


def assign_ocr_labels_to_rooms(
    rooms: List[Dict[str, Any]],
    room_texts: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Assign OCR-detected room labels to the closest detected room polygon.

    For each OCR text that matched a room name, find the room polygon
    whose centroid is nearest to the text position, and update that
    room's label and detected_label fields.

    Args:
        rooms:      Room list from room_detector
        room_texts: Room text list from OCR extractor

    Returns:
        Updated rooms list with OCR labels applied where found
    """
    if not rooms or not room_texts:
        return rooms

    # Compute room centroids
    centroids = []
    for room in rooms:
        poly = room.get("polygon", [])
        if poly:
            cx = sum(p[0] for p in poly) / len(poly)
            cy = sum(p[1] for p in poly) / len(poly)
        else:
            cx, cy = 0.0, 0.0
        centroids.append((cx, cy))

    # Match each OCR text to the nearest room
    for text_info in room_texts:
        tx, ty = text_info["x"], text_info["y"]
        best_room_idx = None
        best_dist = float("inf")

        for idx, (cx, cy) in enumerate(centroids):
            dist = math.sqrt((tx - cx) ** 2 + (ty - cy) ** 2)
            if dist < best_dist:
                best_dist = dist
                best_room_idx = idx

        if best_room_idx is not None and best_dist < 300:
            rooms[best_room_idx]["label"] = text_info["matched_label"]
            rooms[best_room_idx]["detected_label"] = text_info["text"]
            # Upgrade confidence since we have OCR confirmation
            rooms[best_room_idx]["confidence"] = "high"

    return rooms

