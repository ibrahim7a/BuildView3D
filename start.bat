@echo off
:: ============================================================
:: start.bat — BuildView 3D Windows Startup Script
:: ============================================================
:: This script:
::   1. Navigates to the backend directory
::   2. Creates a virtual environment (if it doesn't exist)
::   3. Activates the virtual environment
::   4. Installs all Python dependencies
::   5. Starts the FastAPI backend server
::   6. Opens the browser at the landing page
:: ============================================================

echo.
echo ======================================================
echo   BuildView 3D — Starting Up
echo   See Your Home Before It's Built
echo ======================================================
echo.

:: Change to the backend directory
cd /d D:\BuildView3D\backend

:: ----------------------------------------------------------
:: Step 1: Create virtual environment if it doesn't exist
:: ----------------------------------------------------------
if not exist "venv\" (
    echo [1/4] Creating Python virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo.
        echo ERROR: Failed to create virtual environment.
        echo Make sure Python 3.11+ is installed and added to PATH.
        echo Download Python from: https://www.python.org/downloads/
        echo.
        pause
        exit /b 1
    )
    echo       Virtual environment created successfully.
) else (
    echo [1/4] Virtual environment already exists. Skipping creation.
)

:: ----------------------------------------------------------
:: Step 2: Activate the virtual environment
:: ----------------------------------------------------------
echo [2/4] Activating virtual environment...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo.
    echo ERROR: Failed to activate virtual environment.
    pause
    exit /b 1
)
echo       Virtual environment activated.

:: ----------------------------------------------------------
:: Step 3: Install / update dependencies
:: ----------------------------------------------------------
echo [3/4] Installing Python dependencies (this may take a few minutes)...
pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo.
    echo ERROR: Failed to install dependencies.
    echo Check your internet connection and try again.
    echo.
    pause
    exit /b 1
)
echo       Dependencies installed successfully.

:: ----------------------------------------------------------
:: Step 4: Start the FastAPI server
:: ----------------------------------------------------------
echo [4/4] Starting BuildView 3D backend server...
echo.
echo ======================================================
echo   BuildView 3D is running!
echo.
echo   Landing Page:  http://localhost:8000/app/index.html
echo   Dashboard:     http://localhost:8000/app/dashboard.html
echo   API Docs:      http://localhost:8000/docs
echo   Health Check:  http://localhost:8000/health
echo.
echo   Press Ctrl+C to stop the server.
echo ======================================================
echo.

:: Open the browser (after a 2-second delay to let the server start)
:: Using 'start' opens the URL in the default browser
timeout /t 2 /nobreak >nul
start "" "http://localhost:8000/app/index.html"

:: Start uvicorn — the ASGI server that runs FastAPI
:: --reload means it auto-restarts when you edit Python files
:: --host 0.0.0.0 makes it accessible on your local network too
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

:: This line runs only if the server stops
echo.
echo Server has stopped.
pause
