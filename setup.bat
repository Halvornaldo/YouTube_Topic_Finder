@echo off
REM YouTube Topic Finder - Windows Setup Script

echo =========================================
echo YouTube Topic Finder - Setup Script
echo =========================================
echo.

REM Check Python
echo Checking Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.11+ from https://www.python.org/
    pause
    exit /b 1
)
python --version
echo.

REM Check Docker
echo Checking Docker installation...
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Docker is not installed or not running
    echo Please install Docker Desktop from https://www.docker.com/products/docker-desktop
    pause
    exit /b 1
)
docker --version
echo.

REM Create virtual environment
echo Creating virtual environment...
if not exist "venv" (
    python -m venv venv
    echo Virtual environment created
) else (
    echo Virtual environment already exists
)
echo.

REM Activate virtual environment and install dependencies
echo Installing dependencies...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
echo Dependencies installed
echo.

REM Start Docker containers
echo Starting PostgreSQL and Redis...
docker-compose up -d postgres redis
echo Waiting for database to be ready...
timeout /t 10 /nobreak
echo.

REM Run migrations
echo Running database migrations...
call venv\Scripts\activate.bat
call alembic upgrade head
if %errorlevel% neq 0 (
    echo WARNING: Database migration failed. Make sure virtual environment is activated.
    echo You can run migrations manually: venv\Scripts\activate.bat then alembic upgrade head
)
echo Database setup complete
echo.

echo =========================================
echo Setup Complete!
echo =========================================
echo.
echo Next steps:
echo 1. Make sure your .env file has the Reddit credentials
echo 2. Run: start-server.bat
echo 3. Visit http://localhost:8000/docs
echo.
pause
