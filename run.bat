@echo off
title DocuTrace AI Runner - SS Labz
echo ========================================================
echo               DocuTrace AI App Runner
echo      Developed by SS Labz (https://ss-labz.pages.dev)
echo ========================================================
echo.

:: Check if Docker is installed
where docker >nul 2>nul
if errorlevel 1 goto no_docker

:: Check if Docker daemon is running
echo Checking Docker daemon status...
docker info >nul 2>nul
if errorlevel 1 goto no_daemon

:: Step 1: Start PostgreSQL vector database
echo [1/2] Spinning up PostgreSQL pgvector database container...
docker compose up -d
if errorlevel 1 goto db_failed
echo Database container is online.
echo.

:: Step 2: Launch FastAPI server
echo [2/2] Starting FastAPI gateway app server...
if not exist ".venv\Scripts\python.exe" goto no_venv

echo Gateway server is launching on http://localhost:8008/
echo.
.venv\Scripts\python main.py
if errorlevel 1 goto server_failed

goto end

:no_docker
echo [ERROR] Docker is not installed or not found in your system PATH!
echo Please install Docker Desktop first: https://www.docker.com/products/docker-desktop
echo.
pause
exit /b 1

:no_daemon
echo [ERROR] Docker daemon is not running!
echo Please start Docker Desktop first, wait for it to be ready, and run this script again.
echo.
pause
exit /b 1

:db_failed
echo [ERROR] Failed to start Docker container.
echo.
pause
exit /b 1

:no_venv
echo [ERROR] Virtual environment (.venv) not found!
echo Please run setup instructions in README.md first.
echo.
pause
exit /b 1

:server_failed
echo [ERROR] FastAPI server exited unexpectedly.
echo.
pause
exit /b 1

:end
pause
