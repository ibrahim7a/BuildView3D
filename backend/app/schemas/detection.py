# ============================================================
# schemas/detection.py — Detection Result Pydantic Schemas
# ============================================================
# These schemas define the shape of data for the CV pipeline
# results when exchanged via the API.
# ============================================================

from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime


# ----------------------------------------------------------
# Sub-schemas: Individual detected elements
# ----------------------------------------------------------

class WallSegment(BaseModel):
    """A single detected wall line segment."""
    x1: float
    y1: float
    x2: float
    y2: float
    thickness: float = 10.0
    confidence: str = "medium"   # "high", "medium", "low"


class RoomPolygon(BaseModel):
    """A detected room area."""
    id: str
    label: str
    confidence: str = "medium"
    polygon: List[List[float]]   # [[x,y], [x,y], ...]
    area_sqm: Optional[float] = None
    detected_label: Optional[str] = None  # Raw OCR text from floor plan


class DoorOpening(BaseModel):
    """A detected door gap in a wall."""
    room_id: Optional[str] = None
    wall: Optional[str] = None   # "north", "south", "east", "west"
    x: float
    y: float
    width: float = 90.0
    confidence: str = "medium"


class WindowOpening(BaseModel):
    """A detected window opening in a wall."""
    room_id: Optional[str] = None
    wall: Optional[str] = None
    x: float
    y: float
    width: float = 120.0
    confidence: str = "medium"


class Staircase(BaseModel):
    """A detected staircase area."""
    x: float
    y: float
    width: float
    height: float
    step_count: Optional[int] = None


class DetectionFlag(BaseModel):
    """A warning flag from the CV pipeline for uncertain detections."""
    type: str           # e.g. "unclear_dimension", "low_confidence_room"
    room_id: Optional[str] = None
    message: str


# ----------------------------------------------------------
# Full Detection Result Schema (returned by GET /detection)
# ----------------------------------------------------------

class DetectionResultResponse(BaseModel):
    """
    Full detection result returned by the API.
    Contains all CV pipeline outputs for a project.
    """
    id: int
    project_id: int

    # CV outputs
    walls_data: Optional[List[WallSegment]] = None
    rooms_data: Optional[List[RoomPolygon]] = None
    doors_data: Optional[List[DoorOpening]] = None
    windows_data: Optional[List[WindowOpening]] = None
    staircases_data: Optional[List[Staircase]] = None
    flags: Optional[List[DetectionFlag]] = None

    # Metadata
    overall_confidence: Optional[float] = None
    scale_factor: Optional[float] = None
    image_width_px: Optional[int] = None
    image_height_px: Optional[int] = None
    user_verified: bool = False

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ----------------------------------------------------------
# Schema for user corrections (PUT /detection)
# ----------------------------------------------------------

class DetectionUpdate(BaseModel):
    """
    Schema for user-submitted corrections to a detection result.
    All fields are optional — only send what changed.
    """
    walls_data: Optional[List[WallSegment]] = None
    rooms_data: Optional[List[RoomPolygon]] = None
    doors_data: Optional[List[DoorOpening]] = None
    windows_data: Optional[List[WindowOpening]] = None
    staircases_data: Optional[List[Staircase]] = None
    scale_factor: Optional[float] = None
    user_verified: Optional[bool] = None


# ----------------------------------------------------------
# Lightweight summary (for project list cards)
# ----------------------------------------------------------

class DetectionSummary(BaseModel):
    """
    Brief detection summary shown on project cards.
    Does not include full geometry data.
    """
    overall_confidence: Optional[float] = None
    user_verified: bool = False
    room_count: Optional[int] = None
    wall_count: Optional[int] = None
    flags_count: Optional[int] = None

