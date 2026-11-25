# ============================================================
# routers/upload.py — File Upload API Endpoints
# ============================================================
# Endpoints:
#   POST  /api/v1/projects/{id}/upload   Upload a floor plan file
#   GET   /api/v1/projects/{id}/file     Get file info / preview URL
# ============================================================

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pathlib import Path

from app.database import get_db
from app.models.user import User
from app.schemas.project import ProjectResponse
from app.services.auth_service import get_current_user
from app.services import project_service, file_service

router = APIRouter(
    prefix="/projects",
    tags=["Upload"],
)


@router.post("/{project_id}/upload", response_model=ProjectResponse)
async def upload_floor_plan(
    project_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload a floor plan file (JPG, PNG, or PDF) to a project.

    This endpoint:
      1. Validates the file (type, size, not empty)
      2. Saves the file to: uploads/{user_id}/{project_id}/original.*
      3. For PDFs: converts the first page to PNG for CV processing
      4. Updates the project's floor_plan_path and status → 'uploaded'

    Requires:
        - Bearer token (authenticated user)
        - The project must belong to the current user

    Accepts:
        - file: Multipart form file (JPG, JPEG, PNG, or PDF — max 20 MB)

    Returns:
        Updated project record with status = "uploaded"

    Errors:
        - 400: Invalid file type, too large, or empty
        - 404: Project not found
        - 422: PDF cannot be rendered
    """
    # 1. Verify the project exists and belongs to this user
    project = project_service.get_project_by_id(db, project_id, current_user.id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project #{project_id} was not found."
        )

    # 2. Read the file into memory for validation
    # We read the whole file so we can check size without streaming twice
    file_bytes = await file.read()

    # 3. Validate the file (type, extension, size)
    file_service.validate_floor_plan_file(file, file_bytes)

    # 4. Save to disk (PDF → also converts to PNG)
    relative_path, _processing_path = file_service.save_floor_plan(
        file_bytes=file_bytes,
        filename=file.filename or "upload",
        user_id=current_user.id,
        project_id=project_id,
    )

    # 5. Update the project record in the database
    updated_project = project_service.update_project_floor_plan_path(
        db, project, relative_path
    )

    return updated_project


@router.get("/{project_id}/file")
def get_floor_plan_file(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Serve the uploaded floor plan image for browser preview.

    For PDFs, serves the converted PNG (suitable for canvas display).
    For images, serves the original file.

    Returns:
        The image file directly (FileResponse)

    Errors:
        - 404: Project not found, or no file uploaded yet
    """
    # Verify ownership
    project = project_service.get_project_by_id(db, project_id, current_user.id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project #{project_id} was not found."
        )

    if not project.floor_plan_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No floor plan has been uploaded for this project yet."
        )

    # Reconstruct the full path from the stored relative path
    backend_dir = Path(__file__).parent.parent.parent
    original_path = backend_dir / project.floor_plan_path

    # For PDFs, return the converted PNG instead (browsers can display it)
    if original_path.suffix.lower() == ".pdf":
        png_path = original_path.parent / "converted.png"
        if png_path.exists():
            return FileResponse(
                path=str(png_path),
                media_type="image/png",
                filename=f"floor_plan_{project_id}.png"
            )

    # Return the image file directly
    if not original_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Floor plan file not found on server. Please re-upload."
        )

    # Determine the correct media type
    ext = original_path.suffix.lower()
    media_types = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
    }
    media_type = media_types.get(ext, "application/octet-stream")

    return FileResponse(
        path=str(original_path),
        media_type=media_type,
        filename=f"floor_plan_{project_id}{ext}"
    )

