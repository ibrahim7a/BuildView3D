# ============================================================
# services/auth_service.py — Authentication Business Logic
# ============================================================
# This file contains all the functions related to:
#   - Password hashing and verification
#   - Creating JWT tokens
#   - Looking up and authenticating users
#   - Getting the currently logged-in user from a request
# ============================================================

from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt                    # For creating/decoding JWT tokens
from passlib.context import CryptContext          # For hashing passwords
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.user import User
from app.schemas.user import TokenData

# ----------------------------------------------------------
# Password Hashing Setup
# ----------------------------------------------------------
# We use bcrypt — a one-way hashing algorithm.
# "deprecated=auto" means old hash formats are auto-updated.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ----------------------------------------------------------
# OAuth2 Token Scheme
# ----------------------------------------------------------
# This tells FastAPI where to look for the token in requests.
# Clients must send: Authorization: Bearer <token>
# The tokenUrl is used by the auto-generated Swagger UI.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Check if a plain-text password matches a stored hashed password.

    Args:
        plain_password: The password the user typed in
        hashed_password: The hashed version stored in the database

    Returns:
        True if they match, False if they don't
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hash a plain-text password using bcrypt.

    Args:
        password: The plain-text password to hash

    Returns:
        A bcrypt hash string safe to store in the database
    """
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.

    Args:
        data: Dictionary of data to encode into the token (usually {"sub": email})
        expires_delta: How long until the token expires. If None, uses default.

    Returns:
        A signed JWT token string
    """
    # Make a copy so we don't modify the original
    to_encode = data.copy()

    # Set the expiration time
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    # Add the expiration to the token payload
    to_encode.update({"exp": expire})

    # Encode and sign the token with our secret key
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    return encoded_jwt


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """
    Look up a user by their email address.

    Args:
        db: The database session
        email: The email to search for

    Returns:
        The User object if found, or None if not found
    """
    return db.query(User).filter(User.email == email).first()


def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    """
    Verify a user's email and password.

    Args:
        db: The database session
        email: The user's email
        password: The plain-text password to check

    Returns:
        The User object if credentials are valid, or None if invalid
    """
    # First find the user by email
    user = get_user_by_email(db, email)

    # If no user found with that email, return None
    if not user:
        return None

    # If password doesn't match the stored hash, return None
    if not verify_password(password, user.hashed_password):
        return None

    # Credentials are valid — return the user
    return user


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """
    FastAPI dependency that extracts and validates the current user from a JWT token.

    Use this in routes that require authentication:
        def my_route(current_user: User = Depends(get_current_user)):
            ...

    Args:
        token: JWT token automatically extracted from the Authorization header
        db: Database session

    Returns:
        The authenticated User object

    Raises:
        HTTPException 401: If the token is invalid, expired, or the user doesn't exist
    """
    # This exception is raised if anything goes wrong with the token
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials. Please log in again.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # Decode the token using our secret key
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])

        # The "sub" field contains the user's email
        email: str = payload.get("sub")

        if email is None:
            raise credentials_exception

        # Validate the token data structure
        token_data = TokenData(email=email)

    except JWTError:
        # Token is invalid or expired
        raise credentials_exception

    # Look up the user in the database
    user = get_user_by_email(db, email=token_data.email)

    if user is None:
        raise credentials_exception

    # Check that the account is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This account has been deactivated."
        )

    return user
