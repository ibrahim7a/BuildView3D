# ============================================================
# services/project_service.py — Project Business Logic
# ============================================================
# Contains all database operations for projects.
# Routers call these functions — business logic stays here,
# not inside the router files.
# ============================================================

import uuid
from typing import List, Optional
from sqlalchemy.orm import Session
from datetime import datetime

from app.models.project import Project
from app.schemas.project import ProjectCreate


def create_project(db: Session, user_id: int, project_data: ProjectCreate) -> Project:
    """
    Create a new project record in the database.

    Args:
        db:            Database session
        user_id:       The ID of the user who owns this project
        project_data:  Validated request data (name, description)

    Returns:
        The newly created Project ORM object
    """
    project = Project(
        user_id=user_id,
        name=project_data.name,
        description=project_data.description,
        status="created",
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def get_projects_for_user(
    db: Session,
    user_id: int,
    skip: int = 0,
    limit: int = 50
) -> List[Project]:
    """
    Return all projects owned by a user, newest first.

    Args:
        db:       Database session
        user_id:  Filter to this user's projects only
        skip:     Pagination offset (default 0)
        limit:    Max records to return (default 50)

    Returns:
        List of Project objects
    """
    return (
        db.query(Project)
        .filter(Project.user_id == user_id)
        .order_by(Project.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_project_by_id(db: Session, project_id: int, user_id: int) -> Optional[Project]:
    """
    Fetch a single project by ID, ensuring it belongs to the requesting user.

    Returns None if not found or if the project belongs to a different user.
    This prevents users from accessing each other's projects.

    Args:
        db:          Database session
        project_id:  The project's primary key
        user_id:     The authenticated user's ID (ownership check)

    Returns:
        Project object or None
    """
    return (
        db.query(Project)
        .filter(Project.id == project_id, Project.user_id == user_id)
        .first()
    )


def get_project_by_share_token(db: Session, token: str) -> Optional[Project]:
    """
    Fetch a project by its public share token.
    Used for the public share viewer — no authentication required.

    Args:
        db:     Database session
        token:  The share token from the URL

    Returns:
        Project if found and is_public=True, else None
    """
    return (
        db.query(Project)
        .filter(Project.share_token == token, Project.is_public == True)
        .first()
    )


def update_project_status(
    db: Session,
    project: Project,
    status: str
) -> Project:
    """
    Update a project's status field.

    Valid statuses (from the plan's state machine):
        created → uploaded → analyzing → needs_review / generating → ready
        ready → customizing → ready → shared

    Args:
        db:       Database session
        project:  The Project ORM object to update
        status:   New status string

    Returns:
        Updated Project object
    """
    project.status = status
    project.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(project)
    return project


def update_project_floor_plan_path(
    db: Session,
    project: Project,
    file_path: str
) -> Project:
    """
    Save the uploaded floor plan file path to the project.
    Also advances the project status from 'created' → 'uploaded'.

    Args:
        db:         Database session
        project:    The Project ORM object
        file_path:  Relative path to the saved file (from backend/)

    Returns:
        Updated Project object
    """
    project.floor_plan_path = file_path
    project.status = "uploaded"
    project.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(project)
    return project


def generate_share_token(db: Session, project: Project) -> Project:
    """
    Generate a unique share token for a project and make it public.

    Args:
        db:       Database session
        project:  The Project ORM object

    Returns:
        Updated Project with share_token and is_public=True
    """
    # Generate a unique URL-safe token (e.g. "a3f8c2b1d4e7")
    token = uuid.uuid4().hex[:12]

    # Ensure uniqueness (extremely unlikely to collide but we check)
    while db.query(Project).filter(Project.share_token == token).first():
        token = uuid.uuid4().hex[:12]

    project.share_token = token
    project.is_public = True
    project.status = "shared"
    project.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(project)
    return project


def delete_project(db: Session, project: Project) -> None:
    """
    Delete a project and all its related data from the database.
    File cleanup is handled separately by file_service.

    Args:
        db:       Database session
        project:  The Project ORM object to delete
    """
    db.delete(project)
    db.commit()

