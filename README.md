# GirlfriendCall: Free Cross-Platform Audio Calling App

A simple, direct audio calling application that runs on both Windows and Ubuntu, enabling free calls without relying on third-party services.

## Features

- Direct peer-to-peer audio calls using UDP
- Cross-platform support (Windows and Ubuntu)
- Simple and intuitive GUI
- Shows both local and public IP addresses
- No central servers required
- Zero cost to use

## Prerequisites

- Python 3.6 or higher
- Working microphone and speakers
- Internet connection (for calls over the internet)
- Port forwarding configured on your router for UDP port 5000 (for internet calls)

## Installation

1. Clone or download this repository:
```bash
git clone https://github.com/yourusername/girlfriend-call.git
cd girlfriend-call
```

2. Create a virtual environment (recommended):
```bash
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate
```

3. Install required dependencies:
```bash
pip install -r requirements.txt
```

## Usage

1. Run the application:
```bash
python main.py
```

2. The application window will show:
   - Your Local IP (for calls within the same network)
   - Your Public IP (for calls over the internet)
   - Input field for your girlfriend's IP address
   - Call and Hang Up buttons

3. To make a call:
   - For calls within the same network: Use the Local IP address
   - For calls over the internet: Use the Public IP address
   - Enter the appropriate IP address in the "Girlfriend's IP" field
   - Click "Call Girlfriend" to start the call
   - Click "Hang Up" to end the call

## Network Setup for Internet Calls

1. Port Forwarding:
   - Access your router's configuration page
   - Set up port forwarding for UDP port 5000 to your computer's local IP
   - Both you and your girlfriend need to do this on your respective routers

2. Firewall Configuration:
   - Allow UDP traffic on port 5000 in your firewall settings
   - This is required on both computers

## Troubleshooting

1. Can't hear audio:
   - Check if your microphone and speakers are working
   - Verify the correct audio devices are selected in your system settings
   - Ensure volume levels are appropriate

2. Can't connect:
   - For local network calls:
     - Verify both computers are on the same network
     - Check if the Local IP address is correct
   
   - For internet calls:
     - Verify the Public IP address is correct
     - Check if port forwarding is properly configured
     - Ensure firewalls are not blocking the connection

3. Call quality issues:
   - Try reducing background applications using the network
   - Check your internet connection speed
   - Consider using Local IP if both on same network

## Technical Details

- Audio: Uses PyAudio for audio capture and playback
- Network: UDP sockets for low-latency audio transmission
- GUI: Built with PyQt5 for a native look and feel
- Audio format: 16-bit mono audio at 44.1kHz
- Network protocol: Simple UDP packets containing raw audio data

## Privacy & Security

This application uses direct peer-to-peer connections without any intermediate servers. However, please note:
- Audio data is transmitted unencrypted (raw UDP packets)
- IP addresses must be shared manually between users
- Consider using a VPN if privacy is a concern

## License

This project is open-source and free to use. Feel free to modify and distribute according to your needs.

## Contributing

Contributions are welcome! Please feel free to submit pull requests with improvements or bug fixes.
