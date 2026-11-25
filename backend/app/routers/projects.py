# ============================================================
# routers/projects.py — Project CRUD API Endpoints
# ============================================================
# Endpoints:
#   POST   /api/v1/projects/          Create a new project
#   GET    /api/v1/projects/          List user's projects
#   GET    /api/v1/projects/{id}      Get a single project
#   DELETE /api/v1/projects/{id}      Delete a project
# ============================================================

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.user import User
from app.schemas.project import ProjectCreate, ProjectResponse
from app.services.auth_service import get_current_user
from app.services import project_service, file_service

router = APIRouter(
    prefix="/projects",
    tags=["Projects"],
)


@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    project_data: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new 3D floor plan project.

    Requires authentication (Bearer token).

    Accepts:
        - name: Project display name (required)
        - description: Optional description

    Returns:
        The newly created project record.
    """
    project = project_service.create_project(db, current_user.id, project_data)
    return project


@router.get("/", response_model=List[ProjectResponse])
def list_projects(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List all projects belonging to the current user.

    Returns projects newest first.
    Supports pagination via skip/limit query parameters.
    """
    projects = project_service.get_projects_for_user(
        db, current_user.id, skip=skip, limit=limit
    )
    return projects


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get a single project by ID.

    Only returns the project if it belongs to the current user.

    Errors:
        - 404: Project not found or not owned by current user
    """
    project = project_service.get_project_by_id(db, project_id, current_user.id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project #{project_id} was not found."
        )
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete a project and all its associated files.

    Only the project owner can delete it.

    Errors:
        - 404: Project not found or not owned by current user
    """
    project = project_service.get_project_by_id(db, project_id, current_user.id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project #{project_id} was not found."
        )

    # Delete files from disk first (uploads, outputs, temp)
    file_service.delete_project_files(current_user.id, project_id)

    # Delete the database record (cascades to detection_results)
    project_service.delete_project(db, project)

    # 204 No Content — no body returned
    return None

