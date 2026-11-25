# ============================================================
# schemas/user.py — User Data Schemas (Pydantic)
# ============================================================
# Schemas define what data we accept in requests and what
# data we send back in responses. They handle validation
# automatically — if data is wrong, FastAPI returns an error.
# ============================================================

from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


class UserCreate(BaseModel):
    """
    Schema for creating a new user account.
    Used in the POST /register endpoint.
    """
    # EmailStr automatically validates email format
    email: EmailStr

    # Plain text password (will be hashed before storing)
    password: str

    # User's full display name
    full_name: str

    # Account type — defaults to homeowner if not specified
    account_type: str = "homeowner"


class UserLogin(BaseModel):
    """
    Schema for logging in.
    Used in the POST /login endpoint.
    """
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """
    Schema for returning user information in API responses.
    Never includes the password!
    """
    id: int
    email: str
    full_name: str
    account_type: str
    is_active: bool
    created_at: datetime

    class Config:
        # from_attributes=True allows converting SQLAlchemy model → schema
        from_attributes = True


class Token(BaseModel):
    """
    Schema for the JWT token returned after login/register.
    """
    access_token: str
    token_type: str           # Always "bearer"
    user: UserResponse        # Include user info alongside the token


class TokenData(BaseModel):
    """
    Schema for the data stored inside a JWT token.
    """
    # The email decoded from a valid JWT token
    email: Optional[str] = None
