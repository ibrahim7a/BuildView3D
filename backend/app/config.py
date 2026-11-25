# ============================================================
# config.py — Application Configuration
# ============================================================
# This file loads environment variables from the .env file
# and makes them available as a settings object throughout
# the entire application.
# ============================================================

import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# ----------------------------------------------------------
# Load the .env file from the backend directory
# Path(__file__) is this file (config.py)
# .parent is the app/ directory
# .parent.parent is the backend/ directory (where .env lives)
# ----------------------------------------------------------
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)


class Settings(BaseSettings):
    """
    Settings class — holds all configuration values.
    Pydantic automatically reads from environment variables.
    """

    # Secret key used to sign JWT tokens — keep this private!
    SECRET_KEY: str = "fallback-secret-key-please-set-in-env"

    # Algorithm used to sign the JWT token
    ALGORITHM: str = "HS256"

    # How many minutes a login token stays valid (10080 = 7 days)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080

    # Database connection URL — SQLite stored in backend/ folder
    DATABASE_URL: str = "sqlite:///./buildview3d.db"

    class Config:
        # Tell Pydantic to also read from the .env file
        env_file = str(env_path)
        env_file_encoding = "utf-8"


# ----------------------------------------------------------
# Create a single global settings instance.
# Import this in other files: from app.config import settings
# ----------------------------------------------------------
settings = Settings()
