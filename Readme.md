GirlfriendCall: A Free Cross-Platform Audio Calling App
Project Goal
To create a simple, direct audio calling application that runs on both Windows and Ubuntu, enabling free calls between you and your girlfriend without relying on third-party services or recurring costs.

Core Principles for "No Dime" Development
Peer-to-Peer (P2P): Audio streams directly between your computers, eliminating the need for expensive central servers to relay media.

Open Source: We'll use free and open-source programming languages and libraries.

Cross-Platform: The chosen technologies ensure compatibility with both Windows and Ubuntu.

Minimalist: The focus is purely on essential audio calling functionality to keep it simple and free.

Technology Stack Selection
To ensure absolutely no monetary cost, we'll use the following:

Programming Language:

Python: Easy to learn, quick to prototype, and excellent for cross-platform development. It has rich libraries for audio processing and networking.

GUI (Graphical User Interface) Framework:

PyQt5: This provides Python bindings for the Qt application framework. Qt is a powerful, mature, and widely used cross-platform GUI toolkit that allows your app to have a native look and feel on both Windows and Linux. PyQt5 is available under the LGPL v3 license, which allows free use for open-source projects and personal applications like yours.

Audio Communication:

PyAudio: A Python library for playing and recording audio. It provides a simple way to access your microphone and speakers.

Python socket module (UDP): For direct, real-time audio transmission between your computers. UDP (User Datagram Protocol) is suitable for audio because it prioritizes speed over guaranteed delivery, which is acceptable for voice calls (a lost packet might mean a tiny glitch, but not a dropped call).

Architectural Overview
The application will be structured around two main components:

User Interface (GUI): A simple window where you can enter your girlfriend's IP address, initiate a call, and hang up. It will also display your own IP addresses.

Communication Logic (Backend): This part handles:

Capturing audio from your microphone.

Sending that audio data over the network to your girlfriend's computer.

Receiving audio data from your girlfriend's computer.

Playing the received audio through your speakers.

How a Call Works (Simplified P2P):

Both you and your girlfriend launch the GirlfriendCall app.

Each app will display its own Local IP (for your home network) and attempt to find its Public IP (for calling over the internet).

To make a call, one person (the "caller") enters the other person's Public IP address into the app's input field.

When the "Call" button is pressed, the caller's app starts sending captured microphone audio directly to the receiver's Public IP address and a pre-defined port (e.g., 5000).

The receiver's app is constantly listening on that same port. When it receives audio data, it plays it through the speakers.

Simultaneously, the receiver's app will also be sending their microphone audio back to the caller's Public IP.

Crucial "No Dime" Networking Considerations:

Since we're avoiding paid services for signaling or relaying, you'll need to handle some networking aspects manually:

Public IP Address Exchange: You and your girlfriend will need to manually share your current public IP addresses (e.g., via text message, email, or a quick chat on another platform) before making a call. Your public IP can change, especially for home internet connections (dynamic IP).

NAT (Network Address Translation) and Port Forwarding: Most home routers use NAT, which hides your internal network from the internet. For direct incoming connections, you might need to configure port forwarding on your home router. This tells your router to send any traffic arriving on a specific port (e.g., UDP port 5000) to your computer's local IP address. Both you and your girlfriend might need to do this.

Firewalls: Both Windows and Ubuntu have built-in firewalls. You will need to create exceptions in your firewalls to allow incoming and outgoing UDP traffic on the port your app uses (e.g., 5000).

Detailed Implementation (Python Code)
Here's the code you'll need. Create a directory named girlfriend_call and place these files inside it:

requirements.txt
This file lists the Python libraries your app depends on.

PyQt5
PyAudio
requests

utils.py
This file contains helper functions, particularly for retrieving IP addresses.

import socket
import requests

def get_local_ip():
    """Attempts to find the local IP address of the machine."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Connect to an arbitrary address (doesn't send data) to get the local IP
        # that would be used for outbound connections.
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1' # Fallback to localhost if unable to determine
    finally:
        s.close()
    return IP

def get_public_ip():
    """
    Attempts to get the public IP address using an external API service.
    This requires an internet connection.
    """
    try:
        response = requests.get('https://api.ipify.org').text
        return response
    except Exception:
        return "Failed to fetch (check internet connection)"


call_manager.py
This file contains the core logic for audio capture, playback, and network communication using UDP sockets.

import pyaudio
import socket
import threading
import time

class CallManager:
    # Audio stream configuration constants
    FORMAT = pyaudio.paInt16  # 16-bit audio
    CHANNELS = 1              # Mono audio
    RATE = 44100              # Sample rate (samples per second)
    CHUNK = 1024              # Number of audio frames per buffer (determines latency)
    DEFAULT_PORT = 5000       # Default UDP port for audio communication

    def __init__(self):
        self.p = pyaudio.PyAudio() # Initialize PyAudio
        self.stream_in = None      # Audio input stream (microphone)
        self.stream_out = None     # Audio output stream (speakers)
        self.udp_send_socket = None # UDP socket for sending audio
        self.udp_recv_socket = None # UDP socket for receiving audio
        self.is_calling = False    # Flag to indicate if a call is active
        self.target_ip = None      # IP address of the remote peer
        self.target_port = self.DEFAULT_PORT # Port of the remote peer

        self.audio_send_thread = None # Thread for sending audio
        self.audio_receive_thread = None # Thread for receiving audio

    def start_call(self, target_ip, target_port=DEFAULT_PORT):
        """
        Initiates an audio call to the specified target IP and port.
        """
        if self.is_calling:
            print("CallManager: Already in a call.")
            return

        self.target_ip = target_ip
        self.target_port = target_port
        self.is_calling = True

        print(f"CallManager: Attempting to start call to {self.target_ip}:{self.target_port}")

        try:
            # Open audio input stream (microphone)
            self.stream_in = self.p.open(format=self.FORMAT,
                                         channels=self.CHANNELS,
                                         rate=self.RATE,
                                         input=True,
                                         frames_per_buffer=self.CHUNK,
                                         # Suppress overflow warnings if mic data comes in too fast
                                         exception_on_overflow=False)

            # Open audio output stream (speakers)
            self.stream_out = self.p.open(format=self.FORMAT,
                                          channels=self.CHANNELS,
                                          rate=self.RATE,
                                          output=True,
                                          frames_per_buffer=self.CHUNK)

            # Create UDP socket for sending audio data
            self.udp_send_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

            # Create UDP socket for receiving audio data
            self.udp_recv_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            # Bind the receive socket to listen on all available interfaces on the target port
            self.udp_recv_socket.bind(('', self.target_port))
            # Set a timeout for the receive socket to prevent blocking indefinitely
            self.udp_recv_socket.settimeout(0.5)

            # Start separate threads for sending and receiving audio
            self.audio_send_thread = threading.Thread(target=self._send_audio_loop)
            self.audio_receive_thread = threading.Thread(target=self._receive_audio_loop)

            self.audio_send_thread.start()
            self.audio_receive_thread.start()
            print("CallManager: Call started successfully.")

        except Exception as e:
            print(f"CallManager: Error starting call: {e}")
            self.stop_call() # Clean up if an error occurs during startup
            raise # Re-raise the exception to be handled by the GUI

    def _send_audio_loop(self):
        """Continuously reads audio from the microphone and sends it via UDP."""
        print("CallManager: Audio send thread started.")
        while self.is_calling:
            try:
                # Read audio data from the input stream
                data = self.stream_in.read(self.CHUNK, exception_on_overflow=False)
                # Send the audio data to the target IP and port
                self.udp_send_socket.sendto(data, (self.target_ip, self.target_port))
            except Exception as e:
                if self.is_calling: # Only print error if still in call
                    print(f"CallManager: Error sending audio: {e}")
                self.stop_call() # Stop call on error
                break
            time.sleep(0.001) # Small delay to prevent 100% CPU usage
        print("CallManager: Audio send thread stopped.")

    def _receive_audio_loop(self):
        """Continuously receives audio via UDP and plays it through speakers."""
        print("CallManager: Audio receive thread started.")
        while self.is_calling:
            try:
                # Receive audio data from the UDP socket. Buffer size is CHUNK * 2 for safety.
                data, addr = self.udp_recv_socket.recvfrom(self.CHUNK * 2)
                # Write the received audio data to the output stream
                self.stream_out.write(data)
            except socket.timeout:
                # No data received within the timeout, continue loop
                pass
            except Exception as e:
                if self.is_calling: # Only print error if still in call
                    print(f"CallManager: Error receiving audio: {e}")
                self.stop_call() # Stop call on error
                break
        print("CallManager: Audio receive thread stopped.")

    def stop_call(self):
        """
        Stops the active audio call and cleans up resources.
        """
        if not self.is_calling:
            print("CallManager: No active call to stop.")
            return

        print("CallManager: Stopping call...")
        self.is_calling = False # Set flag to stop threads

        # Wait for threads to finish (with a timeout)
        if self.audio_send_thread and self.audio_send_thread.is_alive():
            self.audio_send_thread.join(timeout=1)
        if self.audio_receive_thread and self.audio_receive_thread.is_alive():
            self.audio_receive_thread.join(timeout=1)

        # Close audio streams if they are open
        if self.stream_in:
            self.stream_in.stop_stream()
            self.stream_in.close()
            self.stream_in = None
        if self.stream_out:
            self.stream_out.stop_stream()
            self.stream_out.close()
            self.stream_out = None

        # Close UDP sockets if they are open
        if self.udp_send_socket:
            self.udp_send_socket.close()
            self.udp_send_socket = None
        if self.udp_recv_socket:
            self.udp_recv_socket.close()
            self.udp_recv_socket = None

        # Terminate PyAudio instance
        self.p.terminate()
        print("CallManager: Call stopped successfully.")


main.py
This is the main application file that sets up the GUI and integrates with the CallManager.

import sys
import threading
import socket # For IP validation
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QLineEdit, QPushButton, QMessageBox)
from PyQt5.QtCore import QTimer, Qt # Import Qt for alignment

from call_manager import CallManager
from utils import get_local_ip, get_public_ip

class GirlfriendCallApp(QWidget):
    def __init__(self):
        super().__init__()
        self.call_manager = CallManager()
        self.init_ui()

    def init_ui(self):
        """Initializes the graphical user interface."""
        self.setWindowTitle('GirlfriendCall')
        self.setGeometry(100, 100, 450, 250) # Set initial window size

        # Main vertical layout for the entire window
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10) # Add some spacing between widgets

        # --- Your IP Information Section ---
        ip_info_group_layout = QVBoxLayout()
        ip_info_group_layout.setSpacing(5)
        ip_info_group_layout.setAlignment(Qt.AlignTop) # Align to top

        # Local IP Label
        self.local_ip_label = QLabel(f"Your Local IP: <b>{get_local_ip()}</b>")
        self.local_ip_label.setTextFormat(Qt.RichText) # Enable HTML-like formatting
        ip_info_group_layout.addWidget(self.local_ip_label)

        # Public IP Label (will be updated asynchronously)
        self.public_ip_label = QLabel(f"Your Public IP: <i>Fetching...</i>")
        self.public_ip_label.setTextFormat(Qt.RichText)
        ip_info_group_layout.addWidget(self.public_ip_label)
        main_layout.addLayout(ip_info_group_layout)

        # Fetch public IP on startup in a separate thread to avoid freezing UI
        self.fetch_public_ip()

        # Set up a timer to periodically update the public IP
        # (useful if your public IP changes frequently, though manual re-entry is still needed for calling)
        self.public_ip_timer = QTimer(self)
        self.public_ip_timer.setInterval(300000) # Every 5 minutes (300,000 ms)
        self.public_ip_timer.timeout.connect(self.fetch_public_ip)
        self.public_ip_timer.start()

        # --- Target IP Input Section ---
        target_ip_layout = QHBoxLayout()
        target_ip_layout.addWidget(QLabel("Girlfriend's IP:"))
        self.target_ip_input = QLineEdit()
        self.target_ip_input.setPlaceholderText("e.g., 192.168.1.100 or 203.0.113.45")
        self.target_ip_input.setToolTip("Enter your girlfriend's Public IP address for internet calls, or Local IP for same-network calls.")
        target_ip_layout.addWidget(self.target_ip_input)
        main_layout.addLayout(target_ip_layout)

        # --- Call Controls Section ---
        button_layout = QHBoxLayout()
        self.call_button = QPushButton("Call Girlfriend")
        self.call_button.clicked.connect(self.start_call)
        button_layout.addWidget(self.call_button)

        self.hangup_button = QPushButton("Hang Up")
        self.hangup_button.clicked.connect(self.stop_call)
        self.hangup_button.setEnabled(False) # Disable initially, enable when call starts
        button_layout.addWidget(self.hangup_button)
        main_layout.addLayout(button_layout)

        # --- Status Label ---
        self.status_label = QLabel("Ready to call.")
        self.status_label.setAlignment(Qt.AlignCenter) # Center the status text
        main_layout.addWidget(self.status_label)

        self.setLayout(main_layout)

    def fetch_public_ip(self):
        """Fetches the public IP address in a separate thread to keep the UI responsive."""
        def _fetch():
            public_ip = get_public_ip()
            # Update the UI element from the main thread using a lambda or signal
            self.public_ip_label.setText(f"Your Public IP: <b>{public_ip}</b>")
        threading.Thread(target=_fetch).start()

    def start_call(self):
        """Handles the logic for initiating a call."""
        target_ip = self.target_ip_input.text().strip()
        if not target_ip:
            QMessageBox.warning(self, "Input Error", "Please enter your girlfriend's IP address.")
            return

        # Basic IP address format validation
        try:
            socket.inet_aton(target_ip) # Checks if it's a valid IPv4 address format
        except socket.error:
            QMessageBox.warning(self, "Input Error", "Invalid IP address format. Please enter a valid IPv4 address (e.g., 203.0.113.45).")
            return

        self.status_label.setText(f"Attempting to call {target_ip}...")
        self.call_button.setEnabled(False)
        self.hangup_button.setEnabled(True)

        try:
            # Start the call in a separate thread to prevent UI freezing
            # The CallManager handles its own internal threads for audio I/O
            threading.Thread(target=self._start_call_thread, args=(target_ip,)).start()
        except Exception as e:
            self.status_label.setText(f"Call failed: {e}")
            self.call_button.setEnabled(True)
            self.hangup_button.setEnabled(False)
            QMessageBox.critical(self, "Call Error", f"Failed to initiate call: {e}\nEnsure microphone/speakers are working and firewall/port forwarding are set up.")

    def _start_call_thread(self, target_ip):
        """Internal method to run call initiation in a separate thread."""
        try:
            self.call_manager.start_call(target_ip, self.call_manager.DEFAULT_PORT)
            self.status_label.setText(f"Connected to {target_ip}!")
        except Exception as e:
            # Update UI elements back on the main thread
            self.status_label.setText(f"Call failed: {e}")
            self.call_button.setEnabled(True)
            self.hangup_button.setEnabled(False)
            QMessageBox.critical(self, "Call Error", f"Failed to start call: {e}\nCheck console for details.")

    def stop_call(self):
        """Handles the logic for ending a call."""
        self.status_label.setText("Hanging up...")
        # Stop the call manager (it handles its own threads)
        self.call_manager.stop_call()
        self.status_label.setText("Call ended. Ready to call.")
        self.call_button.setEnabled(True)
        self.hangup_button.setEnabled(False)

    def closeEvent(self, event):
        """Ensures the call is properly stopped when the application window is closed."""
        if self.call_manager.is_calling:
            self.call_manager.stop_call()
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = GirlfriendCallApp()
    window.show()
    sys.exit(app.exec_())

