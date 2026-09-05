c@echo off
setlocal
set "PYTHONPATH=%~dp0"

:: 1. Prioritize project .venv if present
if exist "%~dp0.venv\Scripts\python.exe" (
    "%~dp0.venv\Scripts\python.exe" -m backend.cli.main %*
    goto :eof
)

:: 2. Check for Python 3.13 where packages are installed
if exist "C:\Users\sarthak\AppData\Local\Programs\Python\Python313\python.exe" (
    "C:\Users\sarthak\AppData\Local\Programs\Python\Python313\python.exe" -m backend.cli.main %*
    goto :eof
)

:: 3. Try py -3.13 launcher
py -3.13 -c "import sys" >nul 2>&1
if %errorlevel% equ 0 (
    py -3.13 -m backend.cli.main %*
    goto :eof
)

:: 4. Fallback to system default python
python -m backend.cli.main %*
endlocal
