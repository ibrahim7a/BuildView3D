# ============================================================
# services/file_service.py — File Upload & Storage Service
# ============================================================
# Handles all file system operations:
#   - Validating uploaded files (type, size)
#   - Saving uploaded floor plan images to disk
#   - Converting PDF pages to PNG images using PyMuPDF
#   - Generating file paths per user/project
#   - Cleanup of temporary files
# ============================================================

import os
import shutil
from pathlib import Path
from typing import Tuple
from fastapi import UploadFile, HTTPException, status

# PyMuPDF — installed as 'pymupdf', imported as 'fitz'
# This is imported lazily inside the PDF function so the app
# still starts if pymupdf is not yet installed.


# ----------------------------------------------------------
# Configuration
# ----------------------------------------------------------

# Backend directory (this file is at backend/app/services/file_service.py)
BACKEND_DIR = Path(__file__).parent.parent.parent

# Where uploaded files are stored
UPLOADS_DIR = BACKEND_DIR / "uploads"

# Where generated output files (3D JSON, thumbnails) are stored
OUTPUTS_DIR = BACKEND_DIR / "outputs"

# Where temporary processing files are stored (cleaned up after use)
TEMP_DIR = BACKEND_DIR / "temp"

# Allowed file types for floor plan uploads
ALLOWED_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "image/jpg",
    "application/pdf",
}

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".pdf"}

# Maximum upload size: 20 MB
MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024  # 20 MB

# DPI for converting PDF pages to PNG (higher = better quality, more memory)
PDF_RENDER_DPI = 150   # 150 DPI: good quality, low memory (8 GB RAM friendly)


# ----------------------------------------------------------
# Directory Helpers
# ----------------------------------------------------------

def get_upload_dir(user_id: int, project_id: int) -> Path:
    """
    Return the upload directory path for a specific project.
    Creates it if it doesn't exist.

    Path structure: uploads/{user_id}/{project_id}/
    """
    path = UPLOADS_DIR / str(user_id) / str(project_id)
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_output_dir(project_id: int) -> Path:
    """
    Return the output directory for a project (3D JSON, thumbnails).
    Creates it if it doesn't exist.

    Path structure: outputs/{project_id}/
    """
    path = OUTPUTS_DIR / str(project_id)
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_temp_dir(project_id: int) -> Path:
    """
    Return the temp directory for a project during processing.
    Creates it if it doesn't exist.

    Path structure: temp/{project_id}/
    """
    path = TEMP_DIR / str(project_id)
    path.mkdir(parents=True, exist_ok=True)
    return path


# ----------------------------------------------------------
# File Validation
# ----------------------------------------------------------

def validate_floor_plan_file(file: UploadFile, file_bytes: bytes) -> None:
    """
    Validate an uploaded floor plan file before saving it.

    Checks:
      1. File extension is allowed (.jpg, .jpeg, .png, .pdf)
      2. MIME type matches allowed types
      3. File size is under the 20 MB limit

    Args:
        file:        The FastAPI UploadFile object (has .filename, .content_type)
        file_bytes:  The raw file content already read into memory

    Raises:
        HTTPException 400: If validation fails (with a clear error message)
    """
    # 1. Check file extension
    filename = file.filename or ""
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"File type '{ext}' is not supported. "
                f"Please upload a JPG, PNG, or PDF file."
            )
        )

    # 2. Check MIME type (content_type sent by the browser)
    content_type = file.content_type or ""
    if content_type not in ALLOWED_MIME_TYPES:
        # Also accept octet-stream for PDFs uploaded from some tools
        if content_type != "application/octet-stream":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Unsupported content type '{content_type}'. "
                    f"Please upload a valid image or PDF file."
                )
            )

    # 3. Check file size
    file_size = len(file_bytes)
    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file is empty. Please select a valid floor plan file."
        )
    if file_size > MAX_FILE_SIZE_BYTES:
        size_mb = file_size / (1024 * 1024)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"File size ({size_mb:.1f} MB) exceeds the 20 MB limit. "
                f"Please reduce the file size and try again."
            )
        )


# ----------------------------------------------------------
# File Saving
# ----------------------------------------------------------

def save_floor_plan(
    file_bytes: bytes,
    filename: str,
    user_id: int,
    project_id: int
) -> Tuple[str, str]:
    """
    Save an uploaded floor plan file to disk.

    For PDFs: saves the original PDF and also converts the first page
    to a PNG image that the CV pipeline can process directly.

    For images (JPG/PNG): saves the file as-is with a standard name.

    Args:
        file_bytes:   Raw bytes of the uploaded file
        filename:     Original filename from the upload (used for extension)
        user_id:      Owning user's ID (used for folder path)
        project_id:   Project ID (used for folder path)

    Returns:
        Tuple of:
          - relative_path: path relative to backend/ (stored in DB)
          - processing_path: absolute path to the image file for CV pipeline
            (for PDFs this is the PNG; for images this is the saved image)
    """
    upload_dir = get_upload_dir(user_id, project_id)
    ext = Path(filename).suffix.lower()

    # Save the original file (always keep the original)
    original_path = upload_dir / f"original{ext}"
    original_path.write_bytes(file_bytes)

    if ext == ".pdf":
        # Convert the PDF first page to PNG for CV processing
        png_path = upload_dir / "converted.png"
        _convert_pdf_to_png(original_path, png_path)
        processing_path = str(png_path)
    else:
        # For images, the original IS the processing image
        processing_path = str(original_path)

    # Return a path relative to the backend directory (for DB storage)
    relative_path = str(original_path.relative_to(BACKEND_DIR))

    return relative_path, processing_path


def _convert_pdf_to_png(pdf_path: Path, output_png_path: Path) -> None:
    """
    Convert the first page of a PDF to a PNG image using PyMuPDF.

    Uses 150 DPI rendering — this gives good quality while keeping
    memory usage low on our 8 GB RAM machine.

    Args:
        pdf_path:        Path to the input PDF file
        output_png_path: Where to save the output PNG

    Raises:
        HTTPException 422: If the PDF cannot be opened or rendered
    """
    try:
        import fitz  # PyMuPDF

        # Open the PDF
        doc = fitz.open(str(pdf_path))

        if doc.page_count == 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="The PDF file appears to be empty (no pages found)."
            )

        # Render the first page at the configured DPI
        page = doc[0]

        # DPI 150 → scale factor = 150/72 ≈ 2.08
        # (PDF default is 72 DPI; we scale up for clarity)
        zoom = PDF_RENDER_DPI / 72.0
        mat = fitz.Matrix(zoom, zoom)

        # Render to a pixmap (RGB image)
        pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB)

        # Save as PNG
        pix.save(str(output_png_path))

        doc.close()

    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "PDF processing is not available. "
                "Please upload a JPG or PNG image instead."
            )
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Could not process PDF file: {str(e)}"
        )


# ----------------------------------------------------------
# Cleanup
# ----------------------------------------------------------

def cleanup_temp_files(project_id: int) -> None:
    """
    Delete all temporary files for a project after processing is complete.

    Args:
        project_id:  The project whose temp files should be removed
    """
    temp_path = TEMP_DIR / str(project_id)
    if temp_path.exists():
        shutil.rmtree(temp_path)


def delete_project_files(user_id: int, project_id: int) -> None:
    """
    Delete all files for a project (uploads + outputs + temp).
    Called when a project is deleted.

    Args:
        user_id:     The owning user's ID
        project_id:  The project to clean up
    """
    # Uploads folder for this project
    upload_path = UPLOADS_DIR / str(user_id) / str(project_id)
    if upload_path.exists():
        shutil.rmtree(upload_path)

    # Outputs folder
    output_path = OUTPUTS_DIR / str(project_id)
    if output_path.exists():
        shutil.rmtree(output_path)

    # Temp folder
    cleanup_temp_files(project_id)

