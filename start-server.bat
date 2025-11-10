@echo off
REM Start YouTube Topic Finder Server

echo =========================================
echo Starting YouTube Topic Finder Server
echo =========================================
echo.

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Start server
echo Starting FastAPI server on http://localhost:8000
echo.
echo Press Ctrl+C to stop the server
echo.
echo API Documentation: http://localhost:8000/docs
echo.

uvicorn src.main:app --reload --port 8000
