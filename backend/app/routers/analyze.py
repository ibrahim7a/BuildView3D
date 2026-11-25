# ============================================================
# routers/analyze.py — CV Pipeline API Endpoints
# ============================================================
# Provides two endpoints:
#
#   POST /api/v1/projects/{project_id}/analyze
#       Triggers the CV pipeline on the uploaded floor plan.
#       Updates project status: uploaded → analyzing → needs_review | generating
#       Saves DetectionResult to the database.
#
#   GET  /api/v1/projects/{project_id}/detection
#       Returns the saved DetectionResult for a project.
# ============================================================

import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.project import Project
from app.models.detection import DetectionResult
from app.schemas.detection import DetectionResultResponse
from app.routers.auth import get_current_user
from app.cv_pipeline.orchestrator import run_pipeline

# ----------------------------------------------------------
# Router setup
# ----------------------------------------------------------
router = APIRouter(
    prefix="/projects",
    tags=["analysis"],
)

# Confidence threshold: results above this go straight to 3D generation,
# results below go to the correction interface for user review.
CONFIDENCE_THRESHOLD = 0.60


# ----------------------------------------------------------
# Helper: resolve the actual image path for a project
# ----------------------------------------------------------
def _resolve_image_path(project: Project) -> str:
    """
    Returns the absolute path to the image file to run the
    CV pipeline on.

    PDFs are converted to PNG on upload (by file_service).
    We prefer the converted PNG; fall back to the original path.
    """
    if not project.floor_plan_path:
        raise HTTPException(
            status_code=400,
            detail="No floor plan has been uploaded for this project yet. "
                   "Please upload a floor plan first."
        )

    original = Path(project.floor_plan_path)

    # If original is a PDF, check for converted PNG sibling
    if original.suffix.lower() == ".pdf":
        converted = original.parent / "converted.png"
        if converted.exists():
            return str(converted)
        # If no converted PNG exists, raise an error
        raise HTTPException(
            status_code=422,
            detail="PDF was uploaded but conversion to PNG is missing. "
                   "Please re-upload the floor plan."
        )

    if not original.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Floor plan file not found on disk. "
                   "The file may have been moved or deleted."
        )

    return str(original)


# ----------------------------------------------------------
# POST /projects/{project_id}/analyze
# ----------------------------------------------------------
@router.post(
    "/{project_id}/analyze",
    response_model=DetectionResultResponse,
    summary="Analyze a floor plan with the CV pipeline",
    description=(
        "Runs the AI/CV pipeline on the uploaded floor plan image. "
        "Detects walls, rooms, doors, windows, and staircases. "
        "Saves results to the database and updates project status."
    ),
)
def analyze_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Trigger CV analysis for a project.

    Flow:
    1. Verify project belongs to current user
    2. Verify a floor plan has been uploaded
    3. Set project status → 'analyzing'
    4. Run the CV pipeline (synchronously for now)
    5. Save DetectionResult to database
    6. Update project status based on confidence score
    7. Return the DetectionResultResponse
    """

    # ----------------------------------------------------------
    # Step 1: Look up the project
    # ----------------------------------------------------------
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user.id,
    ).first()

    if not project:
        raise HTTPException(
            status_code=404,
            detail=f"Project {project_id} not found or you do not have access."
        )

    # ----------------------------------------------------------
    # Step 2: Validate status — allow re-analysis on needs_review
    # ----------------------------------------------------------
    allowed_statuses = {"uploaded", "needs_review", "generating"}
    if project.status not in allowed_statuses and project.status != "analyzing":
        raise HTTPException(
            status_code=400,
            detail=(
                f"Cannot analyze project in status '{project.status}'. "
                "Upload a floor plan first."
            )
        )

    # ----------------------------------------------------------
    # Step 3: Resolve image path
    # ----------------------------------------------------------
    image_path = _resolve_image_path(project)

    # ----------------------------------------------------------
    # Step 4: Mark project as analyzing
    # ----------------------------------------------------------
    project.status = "analyzing"
    db.commit()

    # ----------------------------------------------------------
    # Step 5: Run the CV pipeline
    # ----------------------------------------------------------
    try:
        detection_dict = run_pipeline(image_path)
    except RuntimeError as exc:
        # Pipeline failed — mark project back to uploaded so user can retry
        project.status = "uploaded"
        db.commit()
        raise HTTPException(
            status_code=422,
            detail=f"CV pipeline failed: {exc}"
        )
    except Exception as exc:
        project.status = "uploaded"
        db.commit()
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected analysis error: {exc}"
        )

    # ----------------------------------------------------------
    # Step 6: Save or update DetectionResult in database
    # ----------------------------------------------------------
    existing = db.query(DetectionResult).filter(
        DetectionResult.project_id == project_id
    ).first()

    if existing:
        # Update existing result (re-analysis)
        det = existing
    else:
        # Create new result
        det = DetectionResult(project_id=project_id)
        db.add(det)

    # Serialize list fields to JSON text for SQLite storage
    # NOTE: column names in model use _data suffix (walls_data, rooms_data, etc.)
    # Dimensions are merged into flags as supplementary data since no separate column exists
    flags_with_dims = detection_dict.get("flags", [])
    dims = detection_dict.get("dimensions", [])
    if dims:
        flags_with_dims = list(flags_with_dims) + [
            {"type": "OCR_DIMENSION", "message": str(d)} for d in dims
        ]

    det.walls_data      = json.dumps(detection_dict.get("walls", []))
    det.rooms_data      = json.dumps(detection_dict.get("rooms", []))
    det.doors_data      = json.dumps(detection_dict.get("doors", []))
    det.windows_data    = json.dumps(detection_dict.get("windows", []))
    det.staircases_data = json.dumps(detection_dict.get("staircases", []))
    det.flags           = json.dumps(flags_with_dims)
    det.overall_confidence = detection_dict.get("overall_confidence", 0.0)
    det.scale_factor       = detection_dict.get("scale_factor", 0.05)
    det.image_width_px     = detection_dict.get("image_width_px", 0)
    det.image_height_px    = detection_dict.get("image_height_px", 0)

    db.commit()
    db.refresh(det)

    # ----------------------------------------------------------
    # Step 7: Update project status based on confidence
    # ----------------------------------------------------------
    confidence = detection_dict.get("overall_confidence", 0.0)
    if confidence >= CONFIDENCE_THRESHOLD:
        project.status = "generating"
    else:
        project.status = "needs_review"

    db.commit()
    db.refresh(project)

    # ----------------------------------------------------------
    # Step 8: Build and return response
    # ----------------------------------------------------------
    return _build_response(det)


def _build_response(det: DetectionResult) -> DetectionResultResponse:
    """Helper to build a DetectionResultResponse from a DetectionResult ORM object."""
    return DetectionResultResponse(
        id=det.id,
        project_id=det.project_id,
        walls_data=json.loads(det.walls_data or "[]"),
        rooms_data=json.loads(det.rooms_data or "[]"),
        doors_data=json.loads(det.doors_data or "[]"),
        windows_data=json.loads(det.windows_data or "[]"),
        staircases_data=json.loads(det.staircases_data or "[]"),
        flags=json.loads(det.flags or "[]"),
        overall_confidence=det.overall_confidence,
        scale_factor=det.scale_factor,
        image_width_px=det.image_width_px,
        image_height_px=det.image_height_px,
        user_verified=det.user_verified or False,
        created_at=det.created_at,
        updated_at=det.updated_at,
    )


# ----------------------------------------------------------
# GET /projects/{project_id}/detection
# ----------------------------------------------------------
@router.get(
    "/{project_id}/detection",
    response_model=DetectionResultResponse,
    summary="Get detection results for a project",
    description="Returns the saved CV pipeline results for a project.",
)
def get_detection(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieve saved CV detection results for a project.
    Returns 404 if analysis hasn't been run yet.
    """

    # Verify project ownership
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user.id,
    ).first()

    if not project:
        raise HTTPException(
            status_code=404,
            detail=f"Project {project_id} not found or you do not have access."
        )

    # Look up detection result
    det = db.query(DetectionResult).filter(
        DetectionResult.project_id == project_id
    ).first()

    if not det:
        raise HTTPException(
            status_code=404,
            detail="No detection results found. Run analysis first."
        )

    return _build_response(det)
