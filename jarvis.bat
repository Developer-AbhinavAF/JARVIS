@echo off
:: Move to the directory where the script is located
cd /d "%~dp0"

:: Check if venv exists before trying to activate
if not exist ".\.venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found in .\.venv
    pause
    exit /b
)

:: Activate the virtual environment
call .\.venv\Scripts\activate.bat

:: Run the python script
echo Starting starter.py...
python starter.py

:: Keep window open if the script crashes or finishes
pause
