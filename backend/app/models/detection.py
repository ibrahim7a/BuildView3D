# ============================================================
# models/detection.py — DetectionResults Database Model
# ============================================================
# Stores the output of the CV pipeline for each project.
# After AI/CV analysis runs, results are saved here.
# Users can then review and correct these results before
# 3D generation is triggered.
# ============================================================

from sqlalchemy import Column, Integer, Boolean, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class DetectionResult(Base):
    """
    Stores the structured JSON output from the CV pipeline.
    Maps to the 'detection_results' table.

    One project → one DetectionResult (one-to-one).
    Fields are stored as JSON text because SQLite has no native JSON column.
    SQLAlchemy will store them as TEXT; we serialize/deserialize in the service.
    """

    __tablename__ = "detection_results"

    # ----------------------------------------------------------
    # Primary Key
    # ----------------------------------------------------------
    id = Column(Integer, primary_key=True, autoincrement=True, index=True)

    # ----------------------------------------------------------
    # Foreign Key — links this result to its project
    # ----------------------------------------------------------
    project_id = Column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,      # One result per project (one-to-one)
        index=True
    )

    # ----------------------------------------------------------
    # CV Pipeline Outputs — stored as JSON text
    # ----------------------------------------------------------

    # List of wall segments detected: [{x1,y1,x2,y2,thickness,confidence}, ...]
    walls_data = Column(Text, nullable=True)

    # List of room polygons: [{id, label, polygon, area_sqm, confidence}, ...]
    rooms_data = Column(Text, nullable=True)

    # List of doors: [{room_id, wall, x, y, width, confidence}, ...]
    doors_data = Column(Text, nullable=True)

    # List of windows: [{room_id, wall, x, y, width, confidence}, ...]
    windows_data = Column(Text, nullable=True)

    # List of staircases: [{x, y, width, height, step_count}, ...]
    staircases_data = Column(Text, nullable=True)

    # Warnings and low-confidence flags: [{type, room_id, message}, ...]
    flags = Column(Text, nullable=True)

    # ----------------------------------------------------------
    # Metadata
    # ----------------------------------------------------------

    # Overall pipeline confidence score (0.0 → 1.0)
    overall_confidence = Column(Float, nullable=True)

    # Pixel-to-metre scale factor detected (or user-provided)
    scale_factor = Column(Float, nullable=True)

    # Width and height of the processed image in pixels
    image_width_px = Column(Integer, nullable=True)
    image_height_px = Column(Integer, nullable=True)

    # True once the user has reviewed and confirmed this detection
    user_verified = Column(Boolean, default=False)

    # When the detection was first created
    created_at = Column(DateTime, default=datetime.utcnow)

    # When the user last saved corrections
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # ----------------------------------------------------------
    # Relationships
    # ----------------------------------------------------------

    # Back-reference to the project that owns this result
    project = relationship("Project", back_populates="detection_result")

    def __repr__(self):
        return (
            f"<DetectionResult project_id={self.project_id} "
            f"confidence={self.overall_confidence} verified={self.user_verified}>"
        )

