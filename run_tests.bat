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

:: Install pytest and test dependencies
pip install pytest pytest-cov pytest-mock pytest-timeout black pylint mypy

:: Run the tests
python -m pytest tests/ -v

:: Deactivate virtual environment
deactivate

pause
