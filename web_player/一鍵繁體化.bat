@echo off
cd /d "%~dp0"
echo AI Lyrics Converter - Traditional Chinese
echo ------------------------------------------
echo Running AI Translation...
python ..\scripts\fix_to_traditional.py aurora-song
echo ------------------------------------------
echo Process Finished. Please refresh your web player.
pause
