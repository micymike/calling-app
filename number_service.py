import os
import json
import random
import socket
import threading
import time
from typing import Dict, Optional, Tuple

class NumberService:
    """Service for managing user number assignments and lookups."""
    
    def __init__(self, server_host: str = "127.0.0.1", server_port: int = 5001):
        self.server_host = server_host
        self.server_port = server_port
        
        # Create a unique identifier for this instance
        self.instance_id = str(os.getpid())
        self.data_file = os.path.expanduser(f"~/.girlfriend_call/numbers_{self.instance_id}.json")
        
        self.user_number: Optional[str] = None
        self.is_connected = False
        self._ensure_data_dir()
        
    def _ensure_data_dir(self):
        """Ensure the data directory exists."""
        os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
        
    def register_user(self) -> str:
        """Register user and get a 4-digit number."""
        # First check if we already have a number saved
        saved_number = self._load_saved_number()
        if saved_number:
            self.user_number = saved_number
            return saved_number
            
        # Request a new number from the server
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(5)  # Set timeout to avoid hanging
                sock.connect((self.server_host, self.server_port))
                # Include instance ID in registration request
                sock.sendall(f"REGISTER:{self.instance_id}".encode('utf-8'))
                response = sock.recv(1024).decode('utf-8')
                
                if response.startswith("NUMBER:"):
                    self.user_number = response[7:]
                    self._save_number(self.user_number)
                    return self.user_number
                else:
                    raise ConnectionError(f"Failed to register: {response}")
        except Exception as e:
            print(f"Server connection error: {e}")
            # If server is unavailable, generate a local number
            self.user_number = self._generate_local_number()
            self._save_number(self.user_number)
            return self.user_number
            
    def lookup_number(self, number: str) -> Optional[str]:
        """Look up IP address for a given number."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect((self.server_host, self.server_port))
                sock.sendall(f"LOOKUP:{number}".encode('utf-8'))
                response = sock.recv(1024).decode('utf-8')
                
                if response.startswith("IP:"):
                    return response[3:]
                return None
        except Exception:
            return None
            
    def start_heartbeat(self, local_ip: str):
        """Start sending heartbeats to the server."""
        if not self.user_number:
            raise ValueError("Must register before starting heartbeat")
            
        def _heartbeat_loop():
            while self.is_connected:
                try:
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                        sock.settimeout(5)  # Set timeout to avoid hanging
                        sock.connect((self.server_host, self.server_port))
                        # Include instance ID in heartbeat
                        sock.sendall(f"HEARTBEAT:{self.user_number}:{local_ip}:{self.instance_id}".encode('utf-8'))
                        sock.recv(1024)  # Wait for acknowledgment
                except Exception as e:
                    print(f"Heartbeat error: {e}")
                time.sleep(30)  # Send heartbeat every 30 seconds
                
        self.is_connected = True
        threading.Thread(target=_heartbeat_loop, daemon=True).start()
        
    def stop_heartbeat(self):
        """Stop sending heartbeats."""
        self.is_connected = False
        
    def _generate_local_number(self) -> str:
        """Generate a random 4-digit number locally."""
        return str(random.randint(1000, 9999))
        
    def _save_number(self, number: str):
        """Save the assigned number to a local file."""
        with open(self.data_file, 'w') as f:
            json.dump({"number": number}, f)
            
    def _load_saved_number(self) -> Optional[str]:
        """Load previously assigned number if available."""
        if not os.path.exists(self.data_file):
            return None
            
        try:
            with open(self.data_file, 'r') as f:
                data = json.load(f)
                return data.get("number")
        except Exception:
            return None