@echo off
setlocal

:: Check for Python installation
python --version >nul 2>&1
if errorlevel 1 (
    echo Python is not installed! Please install Python 3.6 or higher.
    pause
    exit /b 1
)

:: Check for virtual environment
if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
)

:: Activate virtual environment
call venv\Scripts\activate.bat

:: Install/upgrade pip
python -m pip install --upgrade pip

:: Install requirements
pip install -r requirements.txt

:: Check for port forwarding
netsh interface portproxy show all | findstr "5000" >nul
if errorlevel 1 (
    echo.
    echo ======================================================================
    echo WARNING: UDP port 5000 might not be forwarded!
    echo For internet calls, you need to:
    echo 1. Configure port forwarding on your router for UDP port 5000
    echo 2. Allow UDP port 5000 in Windows Firewall
    echo ======================================================================
    echo.
)

:: Run the application
echo Starting GirlfriendCall...
python main.py

:: Deactivate virtual environment
deactivate

pause
