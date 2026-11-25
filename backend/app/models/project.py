# ============================================================
# models/project.py — Project Database Model
# ============================================================
# This file defines the Project table in the database.
# Each Project belongs to one User (many-to-one).
# ============================================================

from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class Project(Base):
    """
    Represents a floor plan / 3D model project in the database.
    Maps to the 'projects' table.

    Status flow:
        created → uploaded → analyzing → needs_review → generating → ready
    """

    # The name of the table in the database
    __tablename__ = "projects"

    # ----------------------------------------------------------
    # Columns
    # ----------------------------------------------------------

    # Unique ID for each project, automatically assigned
    id = Column(Integer, primary_key=True, autoincrement=True, index=True)

    # Which user owns this project (links to users.id)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Project display name (e.g., "My Family Home")
    name = Column(String, nullable=False)

    # Optional longer description of the project
    description = Column(String, nullable=True)

    # Current processing status of the project
    # Possible values: created, uploaded, analyzing, needs_review, generating, ready
    status = Column(String, default="created", nullable=False)

    # File path to the uploaded floor plan image (relative to backend/)
    floor_plan_path = Column(String, nullable=True)

    # File path to the generated 3D output file (relative to backend/)
    output_3d_path = Column(String, nullable=True)

    # Scale factor calculated from the floor plan (metres per pixel)
    scale_factor = Column(Float, nullable=True)

    # Unique token used in the public share URL (e.g., /share/abc123)
    share_token = Column(String, unique=True, nullable=True, index=True)

    # Whether this project can be viewed without logging in
    is_public = Column(Boolean, default=False)

    # When the project was created
    created_at = Column(DateTime, default=datetime.utcnow)

    # When the project was last updated — automatically updated on change
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # ----------------------------------------------------------
    # Relationships
    # ----------------------------------------------------------

    # The user who owns this project
    # back_populates="projects" links this to User.projects
    user = relationship("User", back_populates="projects")

    # The CV pipeline detection result for this project (one-to-one)
    # uselist=False → returns a single object instead of a list
    detection_result = relationship(
        "DetectionResult",
        back_populates="project",
        uselist=False,
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        """String representation for debugging."""
        return f"<Project id={self.id} name={self.name} status={self.status}>"
