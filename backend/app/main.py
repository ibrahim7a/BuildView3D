# ============================================================
# main.py — FastAPI Application Entry Point
# ============================================================
# This is the main file that creates and configures the
# FastAPI application. It sets up:
#   - CORS (so the browser frontend can talk to this API)
#   - API routes
#   - Static file serving for the frontend
#   - Database table creation on startup
# ============================================================

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

# Import our database setup
from app.database import engine, Base

# Import all models so they're registered with SQLAlchemy
# (This import triggers models/__init__.py which imports User and Project)
import app.models

# Import the routers (groups of API endpoints)
from app.routers import auth, projects, upload, analyze

# ----------------------------------------------------------
# Create the FastAPI application
# ----------------------------------------------------------
app = FastAPI(
    title="BuildView 3D API",
    version="1.0.0",
    description=(
        "API for BuildView 3D — an AI-powered platform that transforms 2D floor plans "
        "into interactive 3D house models. See your home before it's built."
    ),
    # Where the interactive API docs will be served
    docs_url="/docs",
    redoc_url="/redoc",
)

# ----------------------------------------------------------
# CORS Middleware
# ----------------------------------------------------------
# CORS = Cross-Origin Resource Sharing
# Without this, the browser will block requests from the
# frontend (different port) to the backend API.
# In development, we allow all origins for convenience.
# ----------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # Allow all origins in development
    allow_credentials=True,       # Allow cookies and auth headers
    allow_methods=["*"],          # Allow GET, POST, PUT, DELETE, etc.
    allow_headers=["*"],          # Allow all headers including Authorization
)

# ----------------------------------------------------------
# Include Routers
# ----------------------------------------------------------
# This adds all the /api/v1/auth/... endpoints to the app.
# ----------------------------------------------------------
app.include_router(auth.router, prefix="/api/v1")
app.include_router(projects.router, prefix="/api/v1")
app.include_router(upload.router, prefix="/api/v1")
app.include_router(analyze.router, prefix="/api/v1")

# ----------------------------------------------------------
# Startup Event: Create Database Tables
# ----------------------------------------------------------
# This runs once when the server starts.
# It creates all tables that don't exist yet.
# If tables already exist, it skips them (safe to run again).
# ----------------------------------------------------------
@app.on_event("startup")
def startup_event():
    """Create all database tables on startup."""
    print("🚀 BuildView 3D API is starting up...")
    print("📦 Creating database tables if they don't exist...")
    Base.metadata.create_all(bind=engine)
    print("✅ Database ready!")


# ----------------------------------------------------------
# Root Endpoint
# ----------------------------------------------------------
@app.get("/")
def root():
    """
    Root endpoint — confirms the API is running.
    Visit http://localhost:8000/ to check.
    """
    return {
        "message": "BuildView 3D API is running",
        "version": "1.0.0",
        "docs": "http://localhost:8000/docs",
        "frontend": "http://localhost:8000/app"
    }


# ----------------------------------------------------------
# Health Check Endpoint
# ----------------------------------------------------------
@app.get("/health")
def health_check():
    """
    Health check endpoint.
    Used to verify the API is responding normally.
    """
    return {"status": "healthy", "service": "BuildView 3D API"}


# ----------------------------------------------------------
# Serve the Frontend as Static Files
# ----------------------------------------------------------
# This mounts the frontend/ folder so the browser can load
# the HTML, CSS, and JavaScript files directly from the API.
# Visit: http://localhost:8000/app/index.html
# ----------------------------------------------------------
# Calculate the path to the frontend directory
# This file is at: backend/app/main.py
# frontend is at:  frontend/ (sibling of backend/)
frontend_path = Path(__file__).parent.parent.parent / "frontend"

if frontend_path.exists():
    app.mount("/app", StaticFiles(directory=str(frontend_path), html=True), name="frontend")
    print(f"🌐 Frontend served at: http://localhost:8000/app")
else:
    print(f"⚠️  Frontend directory not found at: {frontend_path}")
