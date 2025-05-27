import pytest
import socket
import threading
import time
from unittest.mock import MagicMock, patch

from socket_manager import SocketManager
from connection_state import ConnectionState, ConnectionManager
from logger import CallLogger

@pytest.fixture
def mock_logger():
    """Create a mock logger."""
    return MagicMock(spec=CallLogger)

@pytest.fixture
def connection_mgr():
    """Create a ConnectionManager instance."""
    return ConnectionManager()

@pytest.fixture
def socket_manager(mock_logger, connection_mgr):
    """Create a SocketManager instance with mocked components."""
    return SocketManager(mock_logger, connection_mgr)

def test_initialization(socket_manager):
    """Test SocketManager initialization."""
    assert socket_manager.send_socket is None
    assert socket_manager.recv_socket is None
    assert socket_manager.target_ip is None
    assert socket_manager.target_port is None
    assert socket_manager.local_port is None
    assert not socket_manager.is_active

@patch('socket.socket')
def test_initialize_success(mock_socket, socket_manager):
    """Test successful socket initialization."""
    mock_socket_instance = MagicMock()
    mock_socket.return_value = mock_socket_instance
    
    result = socket_manager.initialize("127.0.0.1", 5000, 0.5)
    
    assert result is True
    assert socket_manager.is_active
    assert socket_manager.target_ip == "127.0.0.1"
    assert socket_manager.target_port == 5000
    assert mock_socket_instance.setsockopt.called
    assert mock_socket_instance.bind.called
    assert mock_socket_instance.settimeout.called

@patch('socket.socket')
def test_initialize_failure(mock_socket, socket_manager):
    """Test socket initialization failure."""
    mock_socket.side_effect = socket.error("Failed to create socket")
    
    result = socket_manager.initialize("127.0.0.1", 5000)
    
    assert result is False
    assert not socket_manager.is_active
    assert socket_manager.send_socket is None
    assert socket_manager.recv_socket is None
    assert socket_manager.mock_logger.error.called

def test_port_finding(socket_manager):
    """Test port finding functionality."""
    with patch('socket.socket') as mock_socket:
        mock_instance = MagicMock()
        mock_socket.return_value = mock_instance
        
        # Simulate first port being in use
        mock_instance.bind.side_effect = [socket.error(), None]
        
        port = socket_manager._bind_to_available_port(5000, max_attempts=2)
        
        assert port == 5001
        assert mock_instance.bind.call_count == 2

@patch('socket.socket')
def test_send_data(mock_socket, socket_manager):
    """Test sending data through socket."""
    mock_instance = MagicMock()
    mock_socket.return_value = mock_instance
    
    # Initialize socket manager
    socket_manager.initialize("127.0.0.1", 5000)
    
    # Test sending data
    test_data = b"test data"
    result = socket_manager.send(test_data)
    
    assert result is True
    mock_instance.sendto.assert_called_with(test_data, ("127.0.0.1", 5000))

@patch('socket.socket')
def test_receive_data(mock_socket, socket_manager):
    """Test receiving data through socket."""
    mock_instance = MagicMock()
    mock_socket.return_value = mock_instance
    
    # Setup mock receive data
    test_data = b"received data"
    test_addr = ("192.168.1.2", 5000)
    mock_instance.recvfrom.return_value = (test_data, test_addr)
    
    # Initialize socket manager
    socket_manager.initialize("127.0.0.1", 5000)
    
    # Test receiving data
    data, addr = socket_manager.receive()
    
    assert data == test_data
    assert addr == test_addr
    mock_instance.recvfrom.assert_called_once()

def test_cleanup(socket_manager):
    """Test socket cleanup."""
    # Setup mock sockets
    socket_manager.send_socket = MagicMock()
    socket_manager.recv_socket = MagicMock()
    socket_manager._is_active = True
    
    socket_manager.cleanup()
    
    assert not socket_manager.is_active
    assert socket_manager.send_socket is None
    assert socket_manager.recv_socket is None
    assert socket_manager.local_port is None

def test_concurrent_access(socket_manager):
    """Test thread safety of socket operations."""
    with patch('socket.socket') as mock_socket:
        mock_instance = MagicMock()
        mock_socket.return_value = mock_instance
        
        socket_manager.initialize("127.0.0.1", 5000)
        
        def sender():
            for _ in range(100):
                socket_manager.send(b"test")
                time.sleep(0.001)
        
        def receiver():
            for _ in range(100):
                socket_manager.receive()
                time.sleep(0.001)
        
        threads = [
            threading.Thread(target=sender),
            threading.Thread(target=receiver)
        ]
        
        for t in threads:
            t.start()
        
        for t in threads:
            t.join()
        
        # No exceptions should have been raised

def test_socket_reuse(socket_manager):
    """Test socket reuse functionality."""
    with patch('socket.socket') as mock_socket:
        mock_instance = MagicMock()
        mock_socket.return_value = mock_instance
        
        # First initialization
        assert socket_manager.initialize("127.0.0.1", 5000)
        first_send_socket = socket_manager.send_socket
        first_recv_socket = socket_manager.recv_socket
        
        # Second initialization should close previous sockets
        assert socket_manager.initialize("127.0.0.1", 5001)
        assert socket_manager.send_socket != first_send_socket
        assert socket_manager.recv_socket != first_recv_socket
        
        # Verify old sockets were closed
        first_send_socket.close.assert_called_once()
        first_recv_socket.close.assert_called_once()

@patch('socket.socket')
def test_error_handling(mock_socket, socket_manager):
    """Test error handling during socket operations."""
    mock_instance = MagicMock()
    mock_socket.return_value = mock_instance
    
    # Initialize socket manager
    socket_manager.initialize("127.0.0.1", 5000)
    
    # Test send error
    mock_instance.sendto.side_effect = socket.error("Send failed")
    assert not socket_manager.send(b"test")
    assert socket_manager.mock_logger.error.called
    
    # Test receive error
    mock_instance.recvfrom.side_effect = socket.error("Receive failed")
    data, addr = socket_manager.receive()
    assert data is None
    assert addr is None
    
    # Test timeout handling
    mock_instance.recvfrom.side_effect = socket.timeout()
    data, addr = socket_manager.receive()
    assert data is None
    assert addr is None

@patch('socket.socket')
def test_buffer_sizes(mock_socket, socket_manager):
    """Test socket buffer size configuration."""
    mock_instance = MagicMock()
    mock_socket.return_value = mock_instance
    
    socket_manager.initialize("127.0.0.1", 5000)
    
    # Verify buffer sizes were set
    mock_instance.setsockopt.assert_any_call(
        socket.SOL_SOCKET,
        socket.SO_RCVBUF,
        65536
    )
    mock_instance.setsockopt.assert_any_call(
        socket.SOL_SOCKET,
        socket.SO_SNDBUF,
        65536
    )
