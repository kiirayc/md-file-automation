@echo off
REM Run this once (after install_windows.bat) to make the watcher start
REM automatically every time you log in to Windows.

setlocal
set SCRIPT_DIR=%~dp0..
set PYTHONW=%SCRIPT_DIR%\.venv\Scripts\pythonw.exe

if not exist "%PYTHONW%" (
    echo Could not find the virtual environment. Run install_windows.bat first.
    pause
    exit /b 1
)

schtasks /create /tn "MD File Generator" ^
    /tr "\"%PYTHONW%\" -u \"%SCRIPT_DIR%\watch_and_convert.py\"" ^
    /sc onlogon /rl limited /f

if errorlevel 1 (
    echo Failed to create the scheduled task.
    pause
    exit /b 1
)

echo.
echo Auto-start configured: it will launch quietly every time you log in.
echo To start it right now without logging out, run:
echo     schtasks /run /tn "MD File Generator"
echo.
echo To remove auto-start later, run:
echo     schtasks /delete /tn "MD File Generator" /f
pause
