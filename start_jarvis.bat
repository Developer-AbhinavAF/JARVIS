@echo off
echo Starting JARVIS Ultimate...
cd /d "%~dp0"
call .venv\Scripts\activate.bat
python -m jarvis.main
pause

