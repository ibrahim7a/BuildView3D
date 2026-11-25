# ============================================================
# routers/auth.py — Authentication API Endpoints
# ============================================================
# This file defines all the API routes related to:
#   - Registering a new account
#   - Logging in
#   - Getting current user info
# ============================================================

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserLogin, UserResponse, Token
from app.services.auth_service import (
    get_password_hash,
    create_access_token,
    authenticate_user,
    get_user_by_email,
    get_current_user
)

# ----------------------------------------------------------
# Create the router
# All routes in this file will be prefixed with /api/v1
# (the prefix is added when including this router in main.py)
# ----------------------------------------------------------
router = APIRouter(
    prefix="/auth",           # Routes will be: /api/v1/auth/...
    tags=["Authentication"],  # Groups routes in the API docs
)


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user account.

    Accepts:
        - email: Valid email address
        - password: Plain text password (will be hashed)
        - full_name: Display name
        - account_type: "homeowner" or "builder"

    Returns:
        - access_token: JWT token for future authenticated requests
        - token_type: "bearer"
        - user: User information

    Errors:
        - 400: Email already registered
    """
    # ----------------------------------------------------------
    # Step 1: Check if email is already in use
    # ----------------------------------------------------------
    existing_user = get_user_by_email(db, user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists. Please log in instead."
        )

    # ----------------------------------------------------------
    # Step 2: Validate account_type
    # ----------------------------------------------------------
    valid_account_types = ["homeowner", "builder"]
    if user_data.account_type not in valid_account_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"account_type must be one of: {valid_account_types}"
        )

    # ----------------------------------------------------------
    # Step 3: Create the new user
    # ----------------------------------------------------------
    # Hash the password before storing it
    hashed_pw = get_password_hash(user_data.password)

    # Create the User database object
    new_user = User(
        email=user_data.email,
        hashed_password=hashed_pw,
        full_name=user_data.full_name,
        account_type=user_data.account_type,
    )

    # Save to database
    db.add(new_user)
    db.commit()
    db.refresh(new_user)  # Reload from DB to get the auto-assigned id

    # ----------------------------------------------------------
    # Step 4: Create and return a JWT token
    # ----------------------------------------------------------
    token = create_access_token(data={"sub": new_user.email})

    return Token(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(new_user)
    )


@router.post("/login", response_model=Token)
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """
    Log in with email and password.

    Accepts:
        - email: Registered email address
        - password: Plain text password

    Returns:
        - access_token: JWT token
        - token_type: "bearer"
        - user: User information

    Errors:
        - 401: Invalid email or password
    """
    # ----------------------------------------------------------
    # Verify the credentials against the database
    # ----------------------------------------------------------
    user = authenticate_user(db, credentials.email, credentials.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password. Please try again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # ----------------------------------------------------------
    # Create and return the JWT token
    # ----------------------------------------------------------
    token = create_access_token(data={"sub": user.email})

    return Token(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(user)
    )


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """
    Get the currently authenticated user's information.

    Requires:
        - Authorization: Bearer <token> header

    Returns:
        - User information (no password)

    Errors:
        - 401: Not authenticated or token expired
    """
    # get_current_user (the dependency) already looked up the user.
    # We just return them here.
    return current_user
