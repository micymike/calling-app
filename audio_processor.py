import numpy as np
from typing import Optional, Tuple
import audioop
import array
import threading
import time
import queue
from config import AudioConfig


class AudioProcessor:
    """Handles audio processing, including noise reduction and quality improvements."""

    def __init__(self, config: AudioConfig):
        self.config = config
        self.noise_threshold = 300  # Adjustable noise gate threshold
        self.audio_buffer = queue.Queue(maxsize=32)  # Buffer for jitter handling
        self.running = False
        self.processor_thread = None
        self.last_rms = 0
        self.is_speaking = False
        self.vad_threshold = 500  # Voice Activity Detection threshold
        self.gain = 1.0  # Dynamic gain control

        # AGC parameters
        self.target_rms = 4000
        self.agc_min_gain = 0.5
        self.agc_max_gain = 2.0
        self.agc_adjustment_rate = 0.01

    def start(self) -> None:
        """Start the audio processor thread."""
        self.running = True
        self.processor_thread = threading.Thread(target=self._process_buffer)
        self.processor_thread.daemon = True
        self.processor_thread.start()

    def stop(self) -> None:
        """Stop the audio processor thread."""
        self.running = False
        if self.processor_thread:
            self.processor_thread.join(timeout=1.0)
        self.audio_buffer.queue.clear()

    def process_input(self, audio_data: bytes) -> Optional[bytes]:
        """Process input audio data before sending."""
        if not audio_data or len(audio_data) == 0:
            # Return empty buffer if no data
            return bytes(array.array("h", [0] * self.config.chunk_size))
            
        try:
            # Check if audio data is valid
            if len(audio_data) % 2 != 0:
                # Pad with a zero byte if odd length
                audio_data += b'\x00'
                
            # Convert bytes to array for processing
            try:
                audio_array = array.array("h", audio_data)
            except Exception as e:
                # If conversion fails, create a silent buffer
                print(f"Audio conversion error: {e}")
                return bytes(array.array("h", [0] * (len(audio_data) // 2)))

            # Apply noise gate
            if self._calculate_rms(audio_array) < self.noise_threshold:
                return bytes(array.array("h", [0] * len(audio_array)))

            # Apply input processing
            processed = self._apply_input_processing(audio_array)
            return bytes(array.array("h", processed))

        except Exception as e:
            # In case of processing error, log and return silent data
            print(f"Audio processing error: {e}")
            return bytes(array.array("h", [0] * (len(audio_data) // 2)))

    def process_output(self, audio_data: bytes) -> bytes:
        """Process output audio data before playback."""
        # Handle heartbeat packets
        if audio_data == b"heartbeat" or audio_data == b"reconnect_test":
            # Return silent audio for heartbeat packets
            return bytes(array.array("h", [0] * self.config.chunk_size))
            
        try:
            if not audio_data or len(audio_data) == 0:
                # Return silent audio for empty packets
                return bytes(array.array("h", [0] * self.config.chunk_size))

            # Check if audio data is valid
            if len(audio_data) % 2 != 0:
                # Pad with a zero byte if odd length
                audio_data += b'\x00'

            # Add to jitter buffer
            if not self.audio_buffer.full():
                self.audio_buffer.put(audio_data)

            # Get processed data from buffer
            try:
                processed_data = self.audio_buffer.get_nowait()
                return self._apply_output_processing(processed_data)
            except queue.Empty:
                # If buffer is empty, process the current data directly
                return self._apply_output_processing(audio_data)

        except Exception as e:
            # In case of processing error, log and return silent data
            print(f"Output processing error: {e}")
            return bytes(array.array("h", [0] * self.config.chunk_size))

    def _process_buffer(self) -> None:
        """Background thread for processing audio buffer."""
        while self.running:
            try:
                if self.audio_buffer.qsize() > 16:  # If too much delay, clear some
                    while self.audio_buffer.qsize() > 8:
                        self.audio_buffer.get_nowait()
                time.sleep(0.001)
            except Exception:
                continue

    def _apply_input_processing(self, audio_array: array.array) -> array.array:
        """Apply processing to input audio."""
        # Calculate current RMS
        current_rms = self._calculate_rms(audio_array)

        # Update voice activity detection
        self.is_speaking = current_rms > self.vad_threshold

        # Apply Automatic Gain Control (AGC)
        if self.is_speaking:
            if current_rms < self.target_rms:
                self.gain = min(self.gain + self.agc_adjustment_rate, self.agc_max_gain)
            elif current_rms > self.target_rms:
                self.gain = max(self.gain - self.agc_adjustment_rate, self.agc_min_gain)

        # Apply gain
        processed = array.array(
            "h", [int(sample * self.gain) for sample in audio_array]
        )

        # Normalize to prevent clipping
        max_value = max(abs(min(processed)), abs(max(processed)))
        if max_value > 32767:  # Maximum value for 16-bit audio
            scale = 32767 / max_value
            processed = array.array("h", [int(sample * scale) for sample in processed])

        return processed

    def _apply_output_processing(self, audio_data: bytes) -> bytes:
        """Apply processing to output audio."""
        # Convert bytes to array
        audio_array = array.array("h", audio_data)

        # Simple dc offset removal
        dc_offset = int(sum(audio_array) / len(audio_array))
        audio_array = array.array("h", [sample - dc_offset for sample in audio_array])

        # Convert back to bytes
        return bytes(audio_array)

    def _calculate_rms(self, audio_array: array.array) -> float:
        """Calculate Root Mean Square (RMS) of audio data."""
        if len(audio_array) == 0:
            return 0
        squares = sum(sample * sample for sample in audio_array)
        return (squares / len(audio_array)) ** 0.5

    def get_audio_level(self) -> Tuple[float, bool]:
        """Return current audio level (0.0 to 1.0) and speaking status."""
        normalized_rms = min(1.0, self.last_rms / 32767)
        return normalized_rms, self.is_speaking
