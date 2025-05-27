import pytest
import socket
import threading
from unittest.mock import MagicMock, patch
import time

from config import Config, AudioConfig, NetworkConfig
from call_manager import CallManager


@pytest.fixture
def config():
    """Create a test configuration."""
    return Config(
        audio=AudioConfig(chunk_size=512, sample_rate=22050),
        network=NetworkConfig(port=12345, timeout=0.1),
    )


@pytest.fixture
def mock_logger():
    """Create a mock logger."""
    return MagicMock()


@pytest.fixture
def call_manager(config, mock_logger):
    """Create a CallManager instance with mocked components."""
    with patch("call_manager.CallLogger") as mock_logger_class:
        mock_logger_class.return_value = mock_logger
        manager = CallManager(config)
        return manager


def test_init(call_manager, config, mock_logger):
    """Test CallManager initialization."""
    assert call_manager.config == config
    assert call_manager.logger == mock_logger
    assert not call_manager.is_calling
    assert not call_manager.is_muted
    assert call_manager.connection_status == "disconnected"


@patch("pyaudio.PyAudio")
def test_start_call(mock_pyaudio, call_manager):
    """Test starting a call."""
    mock_stream = MagicMock()
    mock_pyaudio.return_value.open.return_value = mock_stream

    test_ip = "127.0.0.1"
    call_manager.start_call(test_ip)

    assert call_manager.is_calling
    assert call_manager.target_ip == test_ip
    assert call_manager.connection_status == "connected"
    assert mock_pyaudio.return_value.open.call_count == 2  # Input and output streams


def test_stop_call(call_manager):
    """Test stopping a call."""
    # Setup mock audio streams and sockets
    call_manager.stream_in = MagicMock()
    call_manager.stream_out = MagicMock()
    call_manager.udp_send_socket = MagicMock()
    call_manager.udp_recv_socket = MagicMock()
    call_manager.audio_processor = MagicMock()
    call_manager.is_calling = True

    call_manager.stop_call()

    assert not call_manager.is_calling
    assert call_manager.connection_status == "disconnected"
    assert call_manager.stream_in is None
    assert call_manager.stream_out is None


def test_toggle_mute(call_manager):
    """Test microphone mute toggling."""
    assert not call_manager.is_muted

    # Test muting
    result = call_manager.toggle_mute()
    assert result is True
    assert call_manager.is_muted

    # Test unmuting
    result = call_manager.toggle_mute()
    assert result is False
    assert not call_manager.is_muted


@pytest.mark.timeout(5)
def test_network_communication():
    """Test actual network communication between two CallManager instances."""
    config1 = Config(network=NetworkConfig(port=12345))
    config2 = Config(network=NetworkConfig(port=12346))

    manager1 = CallManager(config1)
    manager2 = CallManager(config2)

    try:
        # Start call from manager1 to manager2
        thread1 = threading.Thread(target=manager1.start_call, args=("127.0.0.1",))
        thread2 = threading.Thread(target=manager2.start_call, args=("127.0.0.1",))

        thread1.start()
        thread2.start()

        # Wait for connection to establish
        time.sleep(1)

        assert manager1.is_calling
        assert manager2.is_calling
        assert manager1.connection_status == "connected"
        assert manager2.connection_status == "connected"

    finally:
        manager1.stop_call()
        manager2.stop_call()
        thread1.join(timeout=1)
        thread2.join(timeout=1)


def test_reconnection_attempt(call_manager):
    """Test reconnection attempts on connection loss."""
    call_manager.target_ip = "127.0.0.1"
    call_manager.is_calling = True

    with patch("socket.socket") as mock_socket:
        # Simulate first attempt failing, second succeeding
        mock_socket.side_effect = [socket.error, MagicMock()]

        result = call_manager._try_reconnect()
        assert result  # Should succeed on second attempt
        assert mock_socket.call_count == 2


def test_heartbeat_monitoring(call_manager):
    """Test heartbeat monitoring functionality."""
    call_manager.target_ip = "127.0.0.1"
    call_manager.is_calling = True
    call_manager.last_heartbeat = time.time() - 10  # Old heartbeat

    with patch.object(call_manager, "_try_reconnect") as mock_reconnect:
        mock_reconnect.return_value = False

        # Simulate heartbeat check
        call_manager._heartbeat_loop()

        assert mock_reconnect.called
        assert not call_manager.is_calling  # Call should stop after failed reconnection


@patch("pyaudio.PyAudio")
def test_audio_processing_integration(mock_pyaudio, call_manager):
    """Test integration with audio processor."""
    mock_stream = MagicMock()
    mock_pyaudio.return_value.open.return_value = mock_stream

    # Setup test data
    test_audio = bytes([1] * 1024)
    mock_stream.read.return_value = test_audio

    call_manager.start_call("127.0.0.1")

    # Simulate some audio processing
    call_manager._send_audio_loop()

    # Verify audio processor was used
    assert mock_stream.read.called


def test_error_handling(call_manager):
    """Test error handling during call operations."""
    with patch("socket.socket") as mock_socket:
        mock_socket.side_effect = socket.error("Network error")

        with pytest.raises(Exception):
            call_manager.start_call("127.0.0.1")

        assert not call_manager.is_calling
        assert call_manager.connection_status == "failed"


def test_cleanup_on_exit(call_manager):
    """Test cleanup when handling system signals."""
    call_manager.is_calling = True
    call_manager.stream_in = MagicMock()
    call_manager.stream_out = MagicMock()

    # Simulate SIGINT
    call_manager._signal_handler(2, None)

    assert not call_manager.is_calling
    assert call_manager.stream_in is None
    assert call_manager.stream_out is None
