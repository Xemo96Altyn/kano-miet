@echo off
echo ==================================================
echo Launching "IS KANO"
echo ==================================================

REM Searching for .venv
if not exist ".venv\Scripts\activate.bat" (
    echo [ERROR] .venv doesn't exist!
    echo Make sure .venv exists and dependencies are installed:
    echo python -m venv .venv
    echo .venv\Scripts\activate
    echo pip install -r requirements.txt
    pause
    exit /b 1
)

echo [1/3] Activating virtual environment...
call .venv\Scripts\activate.bat

echo [2/3] Launching Flask server (app.py)...
echo [3/3] The server can be accessed from: http://127.0.0.1:8000/
echo ==================================================

python app.py

pause