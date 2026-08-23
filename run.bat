@echo off
title DocuTrace AI Runner - SS Labz
echo ========================================================
echo               DocuTrace AI App Runner
echo      Developed by SS Labz (https://ss-labz.pages.dev)
echo ========================================================
echo.

:: Step 1: Start PostgreSQL vector database
echo [1/2] Spinning up PostgreSQL pgvector database container...
docker compose up -d
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to start Docker container. Ensure Docker Desktop is running!
    pause
    exit /b %ERRORLEVEL%
)
echo Database container is online.
echo.

:: Step 2: Launch FastAPI server
echo [2/2] Starting FastAPI gateway app server...
if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment (.venv) not found!
    echo Please run setup instructions in README.md first.
    pause
    exit /b 1
)

echo Gateway server is launching on http://localhost:8008/
echo.
.venv\Scripts\python main.py
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] FastAPI server exited unexpectedly.
    pause
)
