@echo off
echo Cleaning old processes...
taskkill /F /IM chrome.exe /T >nul 2>&1

echo Starting Chrome...
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="%LOCALAPPDATA%\Google\Chrome\User Data-MurekaDebug" --no-first-run

echo.
echo SUCCESS! Login to Mureka now.
pause
