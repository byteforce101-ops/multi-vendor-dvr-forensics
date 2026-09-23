@echo off
setlocal
set "PYTHONPATH=%~dp0"

:: 1. Prioritize project .venv if present
if exist "%~dp0.venv\Scripts\python.exe" (
    "%~dp0.venv\Scripts\python.exe" -m backend.cli.main %*
    goto :eof
)

:: 2. Try py launcher
py -3 -c "import sys" >nul 2>&1
if %errorlevel% equ 0 (
    py -3 -m backend.cli.main %*
    goto :eof
)

:: 3. Fallback to system default python
python -m backend.cli.main %*
endlocal

