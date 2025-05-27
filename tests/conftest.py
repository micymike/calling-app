import pytest
import os
import sys
import tempfile
from unittest.mock import MagicMock

# Add project root to Python path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import Config, AudioConfig, NetworkConfig


@pytest.fixture
def temp_config_dir():
    """Create a temporary directory for config files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        original_home = os.environ.get("HOME")
        os.environ["HOME"] = tmpdir
        yield tmpdir
        if original_home:
            os.environ["HOME"] = original_home


@pytest.fixture
def mock_pyaudio():
    """Mock PyAudio for testing."""
    mock = MagicMock()
    mock.paInt16 = 8
    mock.get_sample_size.return_value = 2
    return mock


@pytest.fixture
def test_config():
    """Create a test configuration."""
    return Config(
        audio=AudioConfig(
            chunk_size=512,
            sample_rate=22050,
            channels=1,
            format_size=16,
            buffer_size=2048,
        ),
        network=NetworkConfig(
            port=12345,
            timeout=0.1,
            reconnect_attempts=2,
            reconnect_delay=0.5,
            heartbeat_interval=0.5,
        ),
        log_level=20,  # INFO
        log_file="test.log",
        save_settings=False,
    )


@pytest.fixture
def mock_socket():
    """Mock socket for network testing."""
    mock = MagicMock()
    mock.recv.return_value = b"test"
    mock.sendto.return_value = None
    return mock


@pytest.fixture
def mock_audio_stream():
    """Mock audio stream for testing."""
    mock = MagicMock()
    mock.read.return_value = bytes([1] * 1024)
    mock.write.return_value = None
    return mock


@pytest.fixture
def mock_logger():
    """Mock logger for testing."""
    return MagicMock()


@pytest.fixture(autouse=True)
def prevent_real_network():
    """Prevent tests from making real network connections."""
    import socket

    real_socket = socket.socket
    socket.socket = MagicMock()
    yield
    socket.socket = real_socket


@pytest.fixture(autouse=True)
def prevent_real_audio():
    """Prevent tests from accessing real audio devices."""
    import pyaudio

    real_pyaudio = pyaudio.PyAudio
    pyaudio.PyAudio = MagicMock()
    yield
    pyaudio.PyAudio = real_pyaudio


@pytest.fixture
def mock_qt_app():
    """Mock QApplication for GUI testing."""
    from PyQt5.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app
    # No cleanup needed as QApplication will be handled by pytest-qt


@pytest.fixture
def test_env_vars():
    """Set up test environment variables."""
    original_vars = {}
    test_vars = {
        "GIRLFRIEND_CALL_CONFIG": "test_config.json",
        "GIRLFRIEND_CALL_LOG_LEVEL": "DEBUG",
        "GIRLFRIEND_CALL_PORT": "12345",
    }

    # Save original values and set test values
    for key, value in test_vars.items():
        original_vars[key] = os.environ.get(key)
        os.environ[key] = value

    yield test_vars

    # Restore original values
    for key, value in original_vars.items():
        if value is None:
            del os.environ[key]
        else:
            os.environ[key] = value
