# ============================================================
# database.py — Database Connection Setup
# ============================================================
# This file sets up the SQLAlchemy database engine and
# session factory. It also defines the Base class that all
# our database models will inherit from.
# ============================================================

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import settings

# ----------------------------------------------------------
# Create the database engine.
# The engine is the main interface to the database.
# connect_args is needed for SQLite to work with FastAPI's
# async request handling (multiple threads).
# ----------------------------------------------------------
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False}  # Required for SQLite only
)

# ----------------------------------------------------------
# Create a SessionLocal class.
# Each request to the API will get its own database session
# created from this factory.
# autocommit=False means we control when changes are saved.
# autoflush=False means changes aren't sent to DB until commit.
# ----------------------------------------------------------
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# ----------------------------------------------------------
# Create the Base class.
# All database model classes (User, Project, etc.) will
# inherit from this Base class. SQLAlchemy uses it to
# track which tables need to be created.
# ----------------------------------------------------------
Base = declarative_base()


def get_db():
    """
    Database dependency for FastAPI.

    This is a generator function used as a FastAPI dependency.
    It creates a new database session for each request,
    provides it to the route handler, and closes it afterward.

    Usage in a route:
        def my_route(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db          # Give the session to the route handler
    finally:
        db.close()        # Always close the session when done
