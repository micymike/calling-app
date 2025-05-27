from enum import Enum
from threading import Lock
from typing import Optional

class ConnectionState(Enum):
    """Represents the current state of the call connection."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"
    DISCONNECTING = "disconnecting"

class ConnectionManager:
    """Manages connection state and transitions."""
    
    def __init__(self):
        self._state = ConnectionState.DISCONNECTED
        self._state_lock = Lock()
        self._last_error: Optional[str] = None
        
    @property
    def state(self) -> ConnectionState:
        """Get current connection state."""
        with self._state_lock:
            return self._state
            
    @property
    def last_error(self) -> Optional[str]:
        """Get last error message."""
        return self._last_error
        
    def set_state(self, new_state: ConnectionState, error_msg: Optional[str] = None) -> None:
        """
        Transition to a new connection state.
        
        Args:
            new_state: The new state to transition to
            error_msg: Optional error message to store
        """
        with self._state_lock:
            old_state = self._state
            self._state = new_state
            if error_msg is not None:
                self._last_error = error_msg
                
            # Reset error on successful connection
            if new_state == ConnectionState.CONNECTED:
                self._last_error = None
                
    def can_transition_to(self, new_state: ConnectionState) -> bool:
        """
        Check if transitioning to the given state is valid.
        
        Args:
            new_state: The state to check transition to
            
        Returns:
            bool: True if transition is valid, False otherwise
        """
        with self._state_lock:
            # Define valid state transitions
            valid_transitions = {
                ConnectionState.DISCONNECTED: [
                    ConnectionState.CONNECTING
                ],
                ConnectionState.CONNECTING: [
                    ConnectionState.CONNECTED,
                    ConnectionState.FAILED,
                    ConnectionState.DISCONNECTING
                ],
                ConnectionState.CONNECTED: [
                    ConnectionState.RECONNECTING,
                    ConnectionState.DISCONNECTING
                ],
                ConnectionState.RECONNECTING: [
                    ConnectionState.CONNECTED,
                    ConnectionState.FAILED,
                    ConnectionState.DISCONNECTING
                ],
                ConnectionState.FAILED: [
                    ConnectionState.CONNECTING,
                    ConnectionState.DISCONNECTED
                ],
                ConnectionState.DISCONNECTING: [
                    ConnectionState.DISCONNECTED
                ]
            }
            
            return new_state in valid_transitions.get(self._state, [])
