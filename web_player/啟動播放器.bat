@echo off
echo [AURORA] Starting High-Fidelity Music Server...
cd /d "c:\Users\Hao\Desktop\browser-use -mureka"
start http://localhost:8888/index.html
python start_player.py
pause
