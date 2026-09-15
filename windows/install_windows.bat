@echo off
REM Run this once. Requires Python 3.10+ installed from python.org
REM (make sure "Add python.exe to PATH" was checked during install).

setlocal
set SCRIPT_DIR=%~dp0..

echo Creating virtual environment...
python -m venv "%SCRIPT_DIR%\.venv"
if errorlevel 1 (
    echo Could not find "python". Install it from https://python.org and re-run this file.
    pause
    exit /b 1
)

echo Installing dependencies...
"%SCRIPT_DIR%\.venv\Scripts\pip.exe" install -r "%SCRIPT_DIR%\requirements.txt"

echo.
echo Done. Next, double-click setup_autostart.bat in this same folder.
pause
