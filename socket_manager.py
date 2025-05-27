import socket
import threading
import time
from typing import Optional, Tuple, Callable
from logger import CallLogger
from connection_state import ConnectionState, ConnectionManager

class SocketManager:
    """Manages UDP sockets for audio communication."""

    def __init__(self, logger: CallLogger, connection_mgr: ConnectionManager):
        self.logger = logger
        self.connection_mgr = connection_mgr
        self.send_socket: Optional[socket.socket] = None
        self.recv_socket: Optional[socket.socket] = None
        self._socket_lock = threading.Lock()
        self.target_ip: Optional[str] = None
        self.target_port: Optional[int] = None
        self.local_port: Optional[int] = None
        self._is_active = False

    def initialize(self, target_ip: str, target_port: int, timeout: float = 0.5) -> bool:
        """
        Initialize network sockets.

        Args:
            target_ip: Target IP address
            target_port: Target UDP port
            timeout: Socket timeout in seconds

        Returns:
            bool: True if initialization successful, False otherwise
        """
        self.target_ip = target_ip
        self.target_port = target_port

        try:
            with self._socket_lock:
                # Close any existing sockets
                self.cleanup()

                # Create new sockets
                self.send_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self.recv_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

                # Set socket options
                for sock in [self.send_socket, self.recv_socket]:
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)

                # Bind receive socket with port finding
                self.local_port = self._bind_to_available_port(target_port)
                if not self.local_port:
                    raise RuntimeError("Could not find available port")

                self.recv_socket.settimeout(timeout)
                self._is_active = True
                self.connection_mgr.set_state(ConnectionState.CONNECTED)
                return True

        except Exception as e:
            self.logger.error(f"Socket initialization failed: {e}")
            self.cleanup()
            self.connection_mgr.set_state(ConnectionState.FAILED, str(e))
            return False

    def _bind_to_available_port(self, start_port: int, max_attempts: int = 10) -> Optional[int]:
        """
        Try to bind the receive socket to an available port.

        Args:
            start_port: Initial port to try
            max_attempts: Maximum number of ports to try

        Returns:
            int: Bound port number, or None if binding failed
        """
        for port_offset in range(max_attempts):
            try:
                port = start_port + port_offset
                self.recv_socket.bind(("", port))
                if port_offset > 0:
                    self.logger.info(f"Using alternative port: {port}")
                return port
            except OSError as e:
                if port_offset == max_attempts - 1:
                    self.logger.error(f"Failed to bind to any port: {e}")
                    return None
                self.logger.warning(f"Port {port} in use, trying next port")

        return None

    def send(self, data: bytes) -> bool:
        """
        Send data to the target.

        Args:
            data: Bytes to send

        Returns:
            bool: True if send successful, False otherwise
        """
        if not self._is_active or not self.send_socket:
            return False

        try:
            with self._socket_lock:
                if self.send_socket and self.target_ip and self.target_port:
                    self.send_socket.sendto(data, (self.target_ip, self.target_port))
                    return True
        except Exception as e:
            self.logger.error(f"Send failed: {e}")
            return False

        return False

    def receive(self) -> Tuple[Optional[bytes], Optional[Tuple[str, int]]]:
        """
        Receive data from the socket.

        Returns:
            Tuple[Optional[bytes], Optional[Tuple[str, int]]]: (data, address) or (None, None) if receive failed
        """
        if not self._is_active or not self.recv_socket:
            return None, None

        try:
            with self._socket_lock:
                if self.recv_socket:
                    return self.recv_socket.recvfrom(65536)
        except socket.timeout:
            pass
        except Exception as e:
            self.logger.error(f"Receive failed: {e}")

        return None, None

    def cleanup(self) -> None:
        """Clean up network resources."""
        with self._socket_lock:
            self._is_active = False

            for sock_name, sock in [("send", self.send_socket), ("receive", self.recv_socket)]:
                if sock:
                    try:
                        sock.shutdown(socket.SHUT_RDWR)
                    except Exception:
                        pass  # Ignore shutdown errors
                    try:
                        sock.close()
                        self.logger.debug(f"Closed {sock_name} socket")
                    except Exception as e:
                        self.logger.error(f"Error closing {sock_name} socket: {e}")

            self.send_socket = None
            self.recv_socket = None
            self.local_port = None

    @property
    def is_active(self) -> bool:
        """Check if sockets are active and ready."""
        return self._is_active and bool(self.send_socket) and bool(self.recv_socket)

    def get_local_port(self) -> Optional[int]:
        """Get the local port being used."""
        return self.local_port
