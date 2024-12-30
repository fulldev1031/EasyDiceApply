@echo off
REM Navigate to the project directory
cd /d %~dp0

REM Activate the virtual environment
call venv\Scripts\activate

REM Run the Python script
python ui\app.py

REM Pause to see any errors before the window closes
pause