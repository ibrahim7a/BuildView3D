# ============================================================
# models/user.py — User Database Model
# ============================================================
# This file defines the User table in the database.
# Each User can have multiple Projects (one-to-many).
# ============================================================

from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class User(Base):
    """
    Represents a user account in the database.
    Maps to the 'users' table.
    """

    # The name of the table in the database
    __tablename__ = "users"

    # ----------------------------------------------------------
    # Columns (fields in the database table)
    # ----------------------------------------------------------

    # Unique ID for each user, automatically assigned
    id = Column(Integer, primary_key=True, autoincrement=True, index=True)

    # User's email address — must be unique across all users
    email = Column(String, unique=True, index=True, nullable=False)

    # The password stored as a hash (never store plain passwords!)
    hashed_password = Column(String, nullable=False)

    # User's display name
    full_name = Column(String, nullable=False)

    # Type of account: "homeowner" (default) or "builder"
    account_type = Column(String, default="homeowner", nullable=False)

    # Whether the account is active (False = banned/deleted)
    is_active = Column(Boolean, default=True)

    # When the account was created — automatically set to now
    created_at = Column(DateTime, default=datetime.utcnow)

    # ----------------------------------------------------------
    # Relationships
    # ----------------------------------------------------------

    # This user's projects — accessing user.projects gives a list
    # back_populates="user" links this to Project.user
    projects = relationship("Project", back_populates="user")

    def __repr__(self):
        """String representation for debugging."""
        return f"<User id={self.id} email={self.email} type={self.account_type}>"
