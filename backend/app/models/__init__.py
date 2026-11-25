# ============================================================
# models/__init__.py — Register All Models
# ============================================================
# Importing both models here ensures SQLAlchemy knows about
# all tables when we call Base.metadata.create_all().
# Without these imports, tables might not be created.
# ============================================================

from app.models.user import User
from app.models.project import Project
from app.models.detection import DetectionResult
