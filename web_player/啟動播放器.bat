@echo off
title AURORA Pro Player Server
cd /d "%~dp0"
echo --------------------------------------------------
echo   AURORA MUSIC PLAYER - PROFESSIONAL MODE
echo --------------------------------------------------
echo.
echo 正在啟動支援「進度條跳轉」的專用伺服器...
echo 請不要關閉此視窗。
echo.
echo 正在打開瀏覽器: http://localhost:8000
echo.
start "" http://localhost:8000
python range_server.py
pause
