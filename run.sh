#!/bin/bash

# Make script exit on error
set -e

# Check for Python installation
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is not installed! Please install Python 3.6 or higher."
    exit 1
fi

# Function to check if a package is installed (Linux only)
check_package() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if ! dpkg -l | grep -q "^ii  $1"; then
            echo "Required package '$1' is not installed."
            echo "Please install it with: sudo apt-get install $1"
            missing_deps=1
        fi
    fi
}

# Check for required system packages on Linux
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    missing_deps=0
    echo "Checking system dependencies..."
    
    # Check for required packages
    check_package "python3-dev"
    check_package "portaudio19-dev"
    check_package "python3-pyaudio"
    
    if [ $missing_deps -eq 1 ]; then
        echo "Please install the missing dependencies and try again."
        exit 1
    fi
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install/upgrade pip
python -m pip install --upgrade pip

# Install requirements
pip install -r requirements.txt

# Check for port forwarding (Linux only)
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    if ! sudo iptables -L | grep -q "udp dpt:5000"; then
        echo
        echo "======================================================================"
        echo "WARNING: UDP port 5000 might not be forwarded!"
        echo "For internet calls, you need to:"
        echo "1. Configure port forwarding on your router for UDP port 5000"
        echo "2. Allow UDP port 5000 in your firewall:"
        echo "   sudo ufw allow 5000/udp"
        echo "======================================================================"
        echo
    fi
fi

# Check audio devices
echo "Checking audio devices..."
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Check if user is in audio group
    if ! groups | grep -q "audio"; then
        echo "WARNING: Current user is not in the 'audio' group."
        echo "To fix this, run: sudo usermod -a -G audio $USER"
        echo "Then log out and log back in."
    fi
    
    # Check if PulseAudio is running
    if ! pulseaudio --check; then
        echo "WARNING: PulseAudio is not running."
        echo "Starting PulseAudio..."
        pulseaudio --start
    fi
fi

# Run the application
echo "Starting GirlfriendCall..."
python main.py

# Cleanup
deactivate
