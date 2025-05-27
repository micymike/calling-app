import socket
import threading
import json
import os
import time
from typing import Dict, Set

class NumberServer:
    """Simple server to manage user number assignments and lookups."""
    
    def __init__(self, host: str = "0.0.0.0", port: int = 5001):
        self.host = host
        self.port = port
        self.data_file = "number_registry.json"
        self.number_to_ip: Dict[str, str] = {}
        self.used_numbers: Set[str] = set()
        self.last_seen: Dict[str, float] = {}
        self.lock = threading.Lock()
        self._load_registry()
        
    def _load_registry(self):
        """Load existing number registry if available."""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    data = json.load(f)
                    self.number_to_ip = data.get("mappings", {})
                    self.used_numbers = set(self.number_to_ip.keys())
            except Exception as e:
                print(f"Error loading registry: {e}")
                
    def _save_registry(self):
        """Save the current number registry."""
        with open(self.data_file, 'w') as f:
            json.dump({
                "mappings": self.number_to_ip,
                "last_updated": time.time()
            }, f, indent=2)
            
    def _generate_number(self) -> str:
        """Generate a unique 4-digit number."""
        import random
        while True:
            number = str(random.randint(1000, 9999))
            if number not in self.used_numbers:
                return number
                
    def _handle_client(self, client_socket: socket.socket, addr: str):
        """Handle client connection."""
        try:
            data = client_socket.recv(1024).decode('utf-8')
            
            if data.startswith("REGISTER:"):
                # Register new user with instance ID
                instance_id = data.split(":", 1)[1]
                print(f"Registering new user with instance ID: {instance_id} from {addr[0]}")
                
                with self.lock:
                    # Check if this instance already has a number
                    existing_number = None
                    for num, ip in self.number_to_ip.items():
                        if ip.endswith(f":{instance_id}"):
                            existing_number = num
                            break
                    
                    if existing_number:
                        number = existing_number
                        print(f"Returning existing number {number} for instance {instance_id}")
                    else:
                        number = self._generate_number()
                        self.used_numbers.add(number)
                        print(f"Generated new number {number} for instance {instance_id}")
                    
                    # Store IP with instance ID to differentiate instances on same machine
                    self.number_to_ip[number] = f"{addr[0]}:{instance_id}"
                    self.last_seen[number] = time.time()
                    self._save_registry()
                
                client_socket.sendall(f"NUMBER:{number}".encode('utf-8'))
                
            elif data.startswith("LOOKUP:"):
                # Look up IP for a number
                number = data[7:]
                with self.lock:
                    ip_with_instance = self.number_to_ip.get(number, "")
                    # Extract just the IP part without the instance ID
                    ip = ip_with_instance.split(":")[0] if ip_with_instance else ""
                client_socket.sendall(f"IP:{ip if ip else 'NOT_FOUND'}".encode('utf-8'))
                
            elif data.startswith("HEARTBEAT:"):
                # Update user's IP and last seen time
                parts = data.split(":")
                if len(parts) >= 3:
                    number = parts[1]
                    ip = parts[2]
                    instance_id = parts[3] if len(parts) > 3 else ""
                    
                    with self.lock:
                        # Store with instance ID
                        self.number_to_ip[number] = f"{ip}:{instance_id}"
                        self.last_seen[number] = time.time()
                        self._save_registry()
                client_socket.sendall(b"ACK")
                
        except Exception as e:
            print(f"Error handling client {addr}: {e}")
        finally:
            client_socket.close()
            
    def _cleanup_stale_entries(self):
        """Remove entries that haven't sent a heartbeat in a while."""
        while True:
            time.sleep(300)  # Run every 5 minutes
            now = time.time()
            stale_threshold = 3600  # 1 hour
            
            with self.lock:
                stale_numbers = [
                    num for num, last in self.last_seen.items()
                    if now - last > stale_threshold
                ]
                
                for num in stale_numbers:
                    if num in self.number_to_ip:
                        del self.number_to_ip[num]
                    if num in self.last_seen:
                        del self.last_seen[num]
                        
                if stale_numbers:
                    self._save_registry()
                    
    def start(self):
        """Start the number server."""
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            server.bind((self.host, self.port))
            server.listen(5)
            print(f"Number server started on {self.host}:{self.port}")
            
            # Start cleanup thread
            threading.Thread(target=self._cleanup_stale_entries, daemon=True).start()
            
            while True:
                client_sock, address = server.accept()
                client_thread = threading.Thread(
                    target=self._handle_client,
                    args=(client_sock, address)
                )
                client_thread.daemon = True
                client_thread.start()
                
        except KeyboardInterrupt:
            print("Server shutting down...")
        except Exception as e:
            print(f"Error: {e}")
        finally:
            server.close()
            
if __name__ == "__main__":
    server = NumberServer()
    server.start()