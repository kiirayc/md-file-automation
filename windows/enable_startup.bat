@echo off
REM Alternative to setup_autostart.bat for machines where Task Scheduler
REM access is blocked (common on managed/work laptops). Places a small
REM launcher in your personal Startup folder instead - no admin rights needed.

setlocal
set SCRIPT_DIR=%~dp0..
set PYTHONW=%SCRIPT_DIR%\.venv\Scripts\pythonw.exe
set STARTUP_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
set LAUNCHER=%STARTUP_DIR%\md-file-generator-start.bat

if not exist "%PYTHONW%" (
    echo Could not find the virtual environment. Run install_windows.bat first.
    pause
    exit /b 1
)

echo @echo off > "%LAUNCHER%"
echo cd /d "%SCRIPT_DIR%" >> "%LAUNCHER%"
echo start "" "%PYTHONW%" -u "%SCRIPT_DIR%\watch_and_convert.py" >> "%LAUNCHER%"

echo.
echo Auto-start configured (no admin rights needed).
echo Created: "%LAUNCHER%"
echo.
echo It will launch quietly every time you log in.
echo To start it right now without logging out, double-click that file.
echo.
echo To remove auto-start later, delete that file from:
echo     %STARTUP_DIR%
pause
