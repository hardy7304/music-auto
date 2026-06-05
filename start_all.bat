@echo off
cd /d "%~dp0"
title music-auto
echo Starting Chrome...
taskkill /F /IM chrome.exe /T >nul 2>&1
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="%LOCALAPPDATA%\Google\Chrome\User Data-MurekaDebug" --no-first-run
timeout /t 2 >nul
echo Starting Web Server...
".venv\Scripts\python.exe" -m web
pause
