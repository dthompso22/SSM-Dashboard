@echo off
title RA Dashboard
cd /d "%~dp0"

echo.
echo   RA Dashboard
echo   --------------------------------
echo   Pulling latest from git...
git pull --rebase

echo   Starting server at http://localhost:5050
echo   Close this window to stop.
echo.

:: Open browser after 2 seconds (runs in background while Flask starts)
start "" cmd /c "timeout /t 2 /nobreak >nul && start http://localhost:5050"

:: Start Flask (keeps this window open)
python ra_dashboard.py
