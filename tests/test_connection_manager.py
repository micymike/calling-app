import pytest
from connection_state import ConnectionState, ConnectionManager

@pytest.fixture
def connection_mgr():
    """Create a ConnectionManager instance for testing."""
    return ConnectionManager()

def test_initial_state(connection_mgr):
    """Test initial connection state."""
    assert connection_mgr.state == ConnectionState.DISCONNECTED
    assert connection_mgr.last_error is None

def test_state_transitions(connection_mgr):
    """Test valid state transitions."""
    # Test connecting sequence
    assert connection_mgr.can_transition_to(ConnectionState.CONNECTING)
    connection_mgr.set_state(ConnectionState.CONNECTING)
    assert connection_mgr.state == ConnectionState.CONNECTING
    
    # Test successful connection
    assert connection_mgr.can_transition_to(ConnectionState.CONNECTED)
    connection_mgr.set_state(ConnectionState.CONNECTED)
    assert connection_mgr.state == ConnectionState.CONNECTED
    
    # Test reconnection sequence
    assert connection_mgr.can_transition_to(ConnectionState.RECONNECTING)
    connection_mgr.set_state(ConnectionState.RECONNECTING)
    assert connection_mgr.state == ConnectionState.RECONNECTING
    
    # Test disconnection sequence
    assert connection_mgr.can_transition_to(ConnectionState.DISCONNECTING)
    connection_mgr.set_state(ConnectionState.DISCONNECTING)
    assert connection_mgr.state == ConnectionState.DISCONNECTING
    
    assert connection_mgr.can_transition_to(ConnectionState.DISCONNECTED)
    connection_mgr.set_state(ConnectionState.DISCONNECTED)
    assert connection_mgr.state == ConnectionState.DISCONNECTED

def test_invalid_transitions(connection_mgr):
    """Test invalid state transitions."""
    # Cannot go directly from DISCONNECTED to CONNECTED
    assert not connection_mgr.can_transition_to(ConnectionState.CONNECTED)
    
    # Cannot go from CONNECTED to CONNECTING
    connection_mgr.set_state(ConnectionState.CONNECTING)
    connection_mgr.set_state(ConnectionState.CONNECTED)
    assert not connection_mgr.can_transition_to(ConnectionState.CONNECTING)

def test_error_handling(connection_mgr):
    """Test error message handling."""
    error_msg = "Network connection failed"
    connection_mgr.set_state(ConnectionState.FAILED, error_msg)
    
    assert connection_mgr.state == ConnectionState.FAILED
    assert connection_mgr.last_error == error_msg
    
    # Error should clear on successful connection
    connection_mgr.set_state(ConnectionState.CONNECTING)
    connection_mgr.set_state(ConnectionState.CONNECTED)
    assert connection_mgr.last_error is None

def test_connection_failure_recovery(connection_mgr):
    """Test recovery from connection failure."""
    # Simulate failed connection attempt
    connection_mgr.set_state(ConnectionState.CONNECTING)
    connection_mgr.set_state(ConnectionState.FAILED, "Connection timeout")
    
    # Should be able to retry connecting
    assert connection_mgr.can_transition_to(ConnectionState.CONNECTING)
    connection_mgr.set_state(ConnectionState.CONNECTING)
    
    # Simulate successful connection
    assert connection_mgr.can_transition_to(ConnectionState.CONNECTED)
    connection_mgr.set_state(ConnectionState.CONNECTED)
    assert connection_mgr.state == ConnectionState.CONNECTED
    assert connection_mgr.last_error is None

def test_reconnection_sequence(connection_mgr):
    """Test full reconnection sequence."""
    # Initial connection
    connection_mgr.set_state(ConnectionState.CONNECTING)
    connection_mgr.set_state(ConnectionState.CONNECTED)
    
    # Connection lost, attempting reconnect
    assert connection_mgr.can_transition_to(ConnectionState.RECONNECTING)
    connection_mgr.set_state(ConnectionState.RECONNECTING, "Connection lost")
    
    # First reconnection attempt fails
    assert connection_mgr.can_transition_to(ConnectionState.FAILED)
    connection_mgr.set_state(ConnectionState.FAILED, "Reconnection failed")
    
    # Retry connecting
    assert connection_mgr.can_transition_to(ConnectionState.CONNECTING)
    connection_mgr.set_state(ConnectionState.CONNECTING)
    
    # Finally succeed
    connection_mgr.set_state(ConnectionState.CONNECTED)
    assert connection_mgr.state == ConnectionState.CONNECTED
    assert connection_mgr.last_error is None

def test_concurrent_state_access(connection_mgr):
    """Test thread safety of state access."""
    import threading
    import time
    
    def state_changer():
        for _ in range(100):
            if connection_mgr.can_transition_to(ConnectionState.CONNECTING):
                connection_mgr.set_state(ConnectionState.CONNECTING)
            if connection_mgr.can_transition_to(ConnectionState.CONNECTED):
                connection_mgr.set_state(ConnectionState.CONNECTED)
            time.sleep(0.001)

    def state_reader():
        for _ in range(100):
            # These operations should never raise exceptions
            _ = connection_mgr.state
            _ = connection_mgr.last_error
            time.sleep(0.001)

    threads = [
        threading.Thread(target=state_changer),
        threading.Thread(target=state_reader)
    ]

    for t in threads:
        t.start()

    for t in threads:
        t.join()

    # Verify final state is valid
    assert connection_mgr.state in ConnectionState
