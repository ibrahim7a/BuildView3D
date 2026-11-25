# ============================================================
# cv_pipeline/__init__.py
# ============================================================
# Marks this directory as a Python package and exposes the
# main orchestrator function for external use.
# ============================================================

from app.cv_pipeline.orchestrator import run_pipeline

__all__ = ["run_pipeline"]

