@echo off
chcp 65001 >nul
cd /d "%~dp0"
title music-auto 網頁控制台
if not exist ".venv\Scripts\python.exe" (
  echo [錯誤] 找不到 .venv\Scripts\python.exe
  echo 請在此目錄執行: python -m venv .venv
  echo 然後: .venv\Scripts\pip install -r requirements.txt
  pause
  exit /b 1
)
echo.
echo === music-auto 網頁控制台 ===
echo 若曾開過舊視窗，請先關掉舊視窗再跑本檔，否則埠 8765 可能仍為舊程式（會出現 /api/run/stream 404）。
echo 啟動後請用瀏覽器開: http://127.0.0.1:8765
echo 按 Ctrl+C 可停止
echo.
".venv\Scripts\python.exe" -m web
pause
