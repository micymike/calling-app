import pytest
import array
from unittest.mock import MagicMock, patch

from audio_processor import AudioProcessor
from config import AudioConfig


@pytest.fixture
def audio_processor():
    """Create an AudioProcessor instance for testing."""
    config = AudioConfig()
    return AudioProcessor(config)


@pytest.fixture
def mock_audio_data():
    """Create sample audio data for testing."""
    # Create a simple sine wave as test audio data
    data = array.array("h", [0] * 1024)
    for i in range(1024):
        # Scale to fit 16-bit audio range (-32768 to 32767)
        data[i] = int(32767 * (i / 1024))
    return bytes(data)


def test_init_audio_processor():
    """Test AudioProcessor initialization."""
    config = AudioConfig()
    processor = AudioProcessor(config)

    assert processor.config == config
    assert processor.noise_threshold == 300
    assert processor.running is False
    assert processor.processor_thread is None
    assert processor.gain == 1.0


def test_process_input_noise_gate(audio_processor, mock_audio_data):
    """Test noise gate functionality in process_input."""
    # Test with signal below noise threshold
    quiet_data = array.array("h", [100] * 1024)
    result = audio_processor.process_input(bytes(quiet_data))
    processed = array.array("h", result)
    assert all(sample == 0 for sample in processed)

    # Test with signal above noise threshold
    loud_data = array.array("h", [1000] * 1024)
    result = audio_processor.process_input(bytes(loud_data))
    processed = array.array("h", result)
    assert any(sample != 0 for sample in processed)


def test_process_output_empty_data(audio_processor):
    """Test process_output with empty data."""
    result = audio_processor.process_output(b"")
    assert result == b""


def test_process_output_valid_data(audio_processor, mock_audio_data):
    """Test process_output with valid audio data."""
    result = audio_processor.process_output(mock_audio_data)
    assert len(result) == len(mock_audio_data)
    assert result != mock_audio_data  # Should be processed


def test_calculate_rms(audio_processor):
    """Test RMS calculation."""
    # Test with zero signal
    zero_data = array.array("h", [0] * 1024)
    assert audio_processor._calculate_rms(zero_data) == 0

    # Test with constant signal
    constant_data = array.array("h", [1000] * 1024)
    assert audio_processor._calculate_rms(constant_data) == 1000


def test_get_audio_level(audio_processor):
    """Test audio level retrieval."""
    level, speaking = audio_processor.get_audio_level()
    assert 0 <= level <= 1.0
    assert isinstance(speaking, bool)


def test_start_stop(audio_processor):
    """Test starting and stopping the audio processor."""
    audio_processor.start()
    assert audio_processor.running is True
    assert audio_processor.processor_thread is not None
    assert audio_processor.processor_thread.is_alive()

    audio_processor.stop()
    assert audio_processor.running is False
    assert not audio_processor.processor_thread.is_alive()


@patch("time.sleep", return_value=None)
def test_process_buffer(mock_sleep, audio_processor):
    """Test the processing buffer functionality."""
    audio_processor.start()

    # Add some test data to the buffer
    test_data = b"test" * 256
    for _ in range(5):
        audio_processor.audio_buffer.put(test_data)

    # Check buffer processing
    assert audio_processor.audio_buffer.qsize() <= 32  # Should not exceed max size

    audio_processor.stop()


def test_agc_adjustment(audio_processor, mock_audio_data):
    """Test Automatic Gain Control adjustments."""
    # Process quiet audio
    quiet_data = array.array("h", [100] * 1024)
    initial_gain = audio_processor.gain
    audio_processor.process_input(bytes(quiet_data))
    assert audio_processor.gain > initial_gain  # Gain should increase

    # Process loud audio
    loud_data = array.array("h", [30000] * 1024)
    audio_processor.process_input(bytes(loud_data))
    assert audio_processor.gain < initial_gain  # Gain should decrease


def test_dc_offset_removal(audio_processor):
    """Test DC offset removal in output processing."""
    # Create audio with DC offset
    dc_offset = 1000
    test_data = array.array("h", [x + dc_offset for x in range(1024)])
    result = audio_processor._apply_output_processing(bytes(test_data))

    # Convert result back to array for checking
    processed = array.array("h", result)

    # Calculate mean of processed data
    mean = sum(processed) / len(processed)
    assert abs(mean) < dc_offset  # Mean should be closer to zero


def test_error_handling(audio_processor):
    """Test error handling in processing functions."""
    # Test with invalid data
    invalid_data = b"invalid"
    result = audio_processor.process_input(invalid_data)
    assert result == invalid_data  # Should return original data on error

    result = audio_processor.process_output(invalid_data)
    assert result == invalid_data  # Should return original data on error
