@echo off
setlocal EnableDelayedExpansion
title TraceX Multi-Vendor DVR/NVR Forensics Platform

:: ============================================================================
:: TraceX DVR Forensics — One-Click Windows Launcher
:: ============================================================================

set "PROJECT_ROOT=%~dp0"
set "PYTHONPATH=%PROJECT_ROOT%"
cd /d "%PROJECT_ROOT%"

echo ===============================================================================
echo            TraceX Multi-Vendor DVR/NVR Forensic Analysis Platform
echo ===============================================================================
echo.

:: 1. Check Python Virtual Environment
if exist "%PROJECT_ROOT%.venv\Scripts\python.exe" (
    set "PY_EXE=%PROJECT_ROOT%.venv\Scripts\python.exe"
    goto :CHECK_ENV
)

:: 2. Check System Python / py launcher
py -3 -c "import sys" >nul 2>&1
if %errorlevel% equ 0 (
    set "PY_EXE=py -3"
    goto :CHECK_ENV
)

python -c "import sys" >nul 2>&1
if %errorlevel% equ 0 (
    set "PY_EXE=python"
    goto :CHECK_ENV
)

echo [ERROR] Python was not detected on this machine!
echo Please install Python 3.10+ from https://www.python.org/downloads/
echo Make sure to check "Add Python to PATH" during installation.
echo.
pause
exit /b 1

:CHECK_ENV
:: 3. Interactive Menu
echo Select launch mode:
echo   [1] Interactive Forensic TUI Console (Real-time ASCII Player, Search, Dossier)
echo   [2] Start Full Web Platform (FastAPI Backend + Web Dashboard)
echo   [3] Run Step-by-Step Pipeline Wizard
echo   [4] Run System Integrity & Parser Verification Tests
echo   [5] Build Standalone Windows .exe Executable
echo   [0] Exit
echo.
set /p CHOICE="Enter choice [1-5]: "

if "%CHOICE%"=="1" goto :RUN_TUI
if "%CHOICE%"=="2" goto :RUN_WEB
if "%CHOICE%"=="3" goto :RUN_PIPELINE
if "%CHOICE%"=="4" goto :RUN_TESTS
if "%CHOICE%"=="5" goto :BUILD_EXE
if "%CHOICE%"=="0" exit /b 0

:RUN_TUI
cls
%PY_EXE% main.py
goto :END

:RUN_WEB
cls
echo Starting TraceX Backend API Server on http://localhost:8000 ...
start "TraceX Backend" %PY_EXE% -m uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 --reload
if exist "%PROJECT_ROOT%frontend\package.json" (
    echo Starting Frontend Dashboard on http://localhost:5173 ...
    cd "%PROJECT_ROOT%frontend"
    start "TraceX Frontend" npm run dev
    cd /d "%PROJECT_ROOT%"
)
echo.
echo Servers started in background windows.
echo API Docs: http://localhost:8000/docs
echo Web UI:   http://localhost:5173
echo.
pause
goto :END

:RUN_PIPELINE
cls
%PY_EXE% main.py pipeline
goto :END

:RUN_TESTS
cls
%PY_EXE% -m pytest backend/tests/ -q --tb=short
pause
goto :END

:BUILD_EXE
cls
echo Installing build dependencies...
%PY_EXE% -m pip install pyinstaller
echo Compiling standalone Windows .exe...
%PY_EXE% -m PyInstaller --clean --onefile --name "TraceX-DVR-Forensics" --add-data "backend;backend" main.py
echo.
echo Build finished! Check the 'dist' directory for TraceX-DVR-Forensics.exe
pause
goto :END

:END
endlocal
