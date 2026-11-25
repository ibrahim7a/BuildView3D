# ============================================================
# schemas/project.py — Project Data Schemas (Pydantic)
# ============================================================
# Schemas define what data we accept and return for projects.
# ============================================================

from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ProjectCreate(BaseModel):
    """
    Schema for creating a new project.
    Used in the POST /projects endpoint.
    """
    # The project name (required)
    name: str

    # Optional description of the project
    description: Optional[str] = None


class ProjectResponse(BaseModel):
    """
    Schema for returning project info in API responses.
    """
    id: int
    name: str
    description: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime
    share_token: Optional[str] = None

    class Config:
        # Allows converting SQLAlchemy model → schema
        from_attributes = True
