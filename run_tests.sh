#!/bin/bash

# Make script exit on error
set -e

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install/upgrade pip
python -m pip install --upgrade pip

# Install pytest and test dependencies
pip install pytest pytest-cov pytest-mock pytest-timeout black pylint mypy

# Run the tests using python -m to ensure proper module resolution
python -m pytest tests/ -v

# Deactivate virtual environment
deactivate
