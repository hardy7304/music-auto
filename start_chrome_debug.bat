@echo off
chcp 65001 >nul 2>&1
echo ============================================
echo   Chrome Remote Debugging 啟動器
echo ============================================
echo.

REM --- 設定 ---
set CHROME_EXE=C:\Program Files\Google\Chrome\Application\chrome.exe
set DEBUG_PORT=9222
set USER_DATA_DIR=%LOCALAPPDATA%\Google\Chrome\User Data-MurekaDebug

echo [1/3] 關閉所有 Chrome 程序...
taskkill /F /IM chrome.exe >nul 2>&1
timeout /t 3 /nobreak >nul

echo [2/3] 啟動 Chrome（port=%DEBUG_PORT%，profile=%USER_DATA_DIR%）...
start "" "%CHROME_EXE%" --remote-debugging-port=%DEBUG_PORT% --user-data-dir="%USER_DATA_DIR%" --restore-last-session --no-first-run
timeout /t 5 /nobreak >nul

echo [3/3] 驗證連線...
powershell -Command "try { $r = Invoke-WebRequest -Uri 'http://127.0.0.1:%DEBUG_PORT%/json/version' -UseBasicParsing -TimeoutSec 5; Write-Host '[OK] Chrome CDP ready:' ($r.Content | ConvertFrom-Json).Browser } catch { Write-Host '[FAIL]' $_.Exception.Message; exit 1 }"

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ❌ Chrome 啟動失敗。請確認：
    echo    1. Chrome 已安裝在 %CHROME_EXE%
    echo    2. 沒有防火牆擋 port %DEBUG_PORT%
    echo    3. 以系統管理員身分執行此腳本
    pause
    exit /b 1
)

echo.
echo ✅ Chrome 已就緒！
echo    請在 Chrome 中登入 Mureka 並開啟 Create Music 頁面。
echo    然後執行：
echo    .\.venv\Scripts\python -u app\main.py --attach-open-page --from-notion --dry-run true --notion-limit 1
echo.
pause
