@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  echo Creating virtual environment...
  python -m venv .venv || (echo Python was not found. Install Python 3.9+ from python.org and tick "Add to PATH". & pause & exit /b 1)
)
call .venv\Scripts\activate.bat
pip install -q -r requirements.txt || (echo pip install failed. Check your internet connection. & pause & exit /b 1)
echo.
echo Open http://127.0.0.1:5000 in your browser. Press Ctrl+C to stop.
python app.py
pause
