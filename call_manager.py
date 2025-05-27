import os
import time
import signal
import threading
import pyaudio
from typing import Optional, Tuple

from config import Config
from logger import CallLogger
from audio_processor import AudioProcessor
from socket_manager import SocketManager
from connection_state import ConnectionState, ConnectionManager

class CallManager:
    """Manages audio calls including network and audio streams."""

    def __init__(self, config: Config):
        self.config = config
        self.logger = CallLogger(config.log_file, config.log_level)
        
        # Set environment variables to avoid audio system errors
        os.environ['ALSA_CARD'] = 'Generic'
        
        # Initialize managers and processors
        self.connection_mgr = ConnectionManager()
        self.socket_mgr = SocketManager(self.logger, self.connection_mgr)
        
        # Initialize PyAudio with error handling
        try:
            self.p = pyaudio.PyAudio()
        except Exception as e:
            self.logger.error(f"PyAudio initialization error: {e}")
            # Try again with PulseAudio fallback
            os.environ['PULSE_SERVER'] = 'localhost'
            self.p = pyaudio.PyAudio()
            
        self.audio_processor = AudioProcessor(config.audio)

        # Audio streams
        self.stream_in: Optional[pyaudio.Stream] = None
        self.stream_out: Optional[pyaudio.Stream] = None

        # State management
        self.is_calling = False
        self.is_muted = False
        self.target_ip: Optional[str] = None
        self.target_port = config.network.port
        self.last_heartbeat = 0

        # Threading
        self.audio_send_thread: Optional[threading.Thread] = None
        self.audio_receive_thread: Optional[threading.Thread] = None
        self.heartbeat_thread: Optional[threading.Thread] = None

        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        self.logger.info("CallManager initialized")

    def start_call(self, target_ip: str, target_port: Optional[int] = None) -> None:
        """Start an audio call to the specified target."""
        if self.is_calling:
            self.logger.warning("Already in a call")
            return

        if target_port is None:
            target_port = self.config.network.port

        self.target_ip = target_ip
        self.target_port = target_port
        self.is_calling = True
        
        self.connection_mgr.set_state(ConnectionState.CONNECTING)
        self.logger.info(f"Initiating call to {target_ip}:{target_port}")

        try:
            # Initialize audio streams
            self._setup_audio_streams()
            
            # Initialize network sockets
            if not self.socket_mgr.initialize(target_ip, target_port, self.config.network.timeout):
                raise RuntimeError("Failed to initialize network connection")

            # Start audio processor
            self.audio_processor.start()

            # Start communication threads
            self._start_communication_threads()
            
        except Exception as e:
            self.logger.error("Failed to start call", exc_info=e)
            self.stop_call()
            raise

    def _setup_audio_streams(self) -> None:
        """Initialize audio input and output streams."""
        try:
            self.stream_in = self.p.open(
                format=pyaudio.paInt16,
                channels=self.config.audio.channels,
                rate=self.config.audio.sample_rate,
                input=True,
                frames_per_buffer=self.config.audio.chunk_size,
            )

            self.stream_out = self.p.open(
                format=pyaudio.paInt16,
                channels=self.config.audio.channels,
                rate=self.config.audio.sample_rate,
                output=True,
                frames_per_buffer=self.config.audio.chunk_size,
            )
        except Exception as e:
            self.logger.error("Failed to setup audio streams", exc_info=e)
            raise

    def _start_communication_threads(self) -> None:
        """Start all communication-related threads."""
        threads = [
            (self._send_audio_loop, "audio_send"),
            (self._receive_audio_loop, "audio_receive"),
            (self._heartbeat_loop, "heartbeat")
        ]

        for target, name in threads:
            thread = threading.Thread(target=target, name=name, daemon=True)
            setattr(self, f"{name}_thread", thread)
            thread.start()
            self.logger.debug(f"Started {name} thread")

    def _send_audio_loop(self) -> None:
        """Send audio data continuously."""
        reconnect_attempts = 0
        self.logger.debug("Audio send thread started")

        while self.is_calling:
            try:
                if self.is_muted:
                    time.sleep(0.001)
                    continue

                data = self.stream_in.read(
                    self.config.audio.chunk_size,
                    exception_on_overflow=False
                )
                
                processed_data = self.audio_processor.process_input(data)
                if not processed_data:
                    continue

                if self.socket_mgr.send(processed_data):
                    reconnect_attempts = 0
                else:
                    reconnect_attempts += 1
                    if reconnect_attempts >= self.config.network.reconnect_attempts:
                        self.logger.error("Failed to send audio after multiple attempts")
                        self.stop_call()
                        break

            except Exception as e:
                self.logger.error("Error in audio send loop", exc_info=e)
                if not self._try_reconnect():
                    break

            time.sleep(0.001)

        self.logger.debug("Audio send thread stopped")

    def _receive_audio_loop(self) -> None:
        """Receive and play audio data continuously."""
        no_data_count = 0
        self.logger.debug("Audio receive thread started")

        while self.is_calling:
            try:
                data, addr = self.socket_mgr.receive()
                if data:
                    processed_data = self.audio_processor.process_output(data)
                    self.stream_out.write(processed_data)
                    no_data_count = 0
                    self.last_heartbeat = time.time()
                else:
                    no_data_count += 1
                    if no_data_count > self.config.network.reconnect_attempts:
                        self.logger.warning("No audio data received for extended period")
                        if not self._try_reconnect():
                            break
                        no_data_count = 0

            except Exception as e:
                self.logger.error("Error in audio receive loop", exc_info=e)
                if not self._try_reconnect():
                    break

        self.logger.debug("Audio receive thread stopped")

    def _heartbeat_loop(self) -> None:
        """Monitor connection health with heartbeat signals."""
        self.logger.debug("Heartbeat thread started")

        while self.is_calling:
            try:
                # Send heartbeat
                if not self.socket_mgr.send(b"heartbeat"):
                    self.logger.warning("Failed to send heartbeat")
                    if not self._try_reconnect():
                        break

                # Check last received heartbeat
                if time.time() - self.last_heartbeat > self.config.network.timeout * 3:
                    self.logger.warning("No heartbeat received, connection may be lost")
                    if not self._try_reconnect():
                        break

            except Exception as e:
                self.logger.error("Error in heartbeat loop", exc_info=e)
                if not self._try_reconnect():
                    break

            time.sleep(self.config.network.heartbeat_interval)

        self.logger.debug("Heartbeat thread stopped")

    def _try_reconnect(self) -> bool:
        """Attempt to reestablish connection."""
        if not self.is_calling:
            return False

        self.connection_mgr.set_state(ConnectionState.RECONNECTING)
        
        for attempt in range(self.config.network.reconnect_attempts):
            try:
                self.logger.info(f"Attempting to reconnect... (attempt {attempt + 1}/{self.config.network.reconnect_attempts})")
                
                # Reinitialize network connection
                if self.socket_mgr.initialize(self.target_ip, self.target_port, self.config.network.timeout):
                    self.connection_mgr.set_state(ConnectionState.CONNECTED)
                    return True
                    
            except Exception as e:
                self.logger.error(f"Reconnection attempt {attempt + 1} failed", exc_info=e)
                
            time.sleep(self.config.network.reconnect_delay)

        self.logger.error("Reconnection failed after multiple attempts")
        self.stop_call()
        return False

    def stop_call(self) -> None:
        """Stop the current call and clean up resources."""
        if not self.is_calling:
            return

        self.logger.info("Stopping call...")
        self.is_calling = False
        self.connection_mgr.set_state(ConnectionState.DISCONNECTING)

        try:
            # Stop audio processor
            if hasattr(self, "audio_processor"):
                self.audio_processor.stop()

            # Clean up network resources
            self.socket_mgr.cleanup()

            # Close audio streams
            for stream in [self.stream_in, self.stream_out]:
                if stream:
                    try:
                        stream.stop_stream()
                        stream.close()
                    except Exception as e:
                        self.logger.error(f"Error closing audio stream: {e}")

            self.stream_in = None
            self.stream_out = None

            # Wait for threads to finish
            self._wait_for_threads()

            # Clean up PyAudio
            self._cleanup_pyaudio()

            # Save settings if needed
            if self.target_ip and self.config.save_settings:
                self.config.last_called_ip = self.target_ip
                self.config.save()

        except Exception as e:
            self.logger.error("Error during call cleanup", exc_info=e)
        finally:
            self.connection_mgr.set_state(ConnectionState.DISCONNECTED)
            self.logger.info("Call stopped")

    def _wait_for_threads(self, timeout: float = 1.0) -> None:
        """Wait for all threads to finish."""
        threads = [
            (self.audio_send_thread, "Audio send"),
            (self.audio_receive_thread, "Audio receive"),
            (self.heartbeat_thread, "Heartbeat")
        ]

        for thread, name in threads:
            if thread and thread.is_alive():
                thread.join(timeout=timeout)
                if thread.is_alive():
                    self.logger.warning(f"{name} thread did not stop cleanly")

    def _cleanup_pyaudio(self) -> None:
        """Clean up PyAudio resources and reinitialize if needed."""
        try:
            self.p.terminate()
            
            # Reinitialize PyAudio for future calls
            self.p = pyaudio.PyAudio()
        except Exception as e:
            self.logger.error("Error during PyAudio cleanup", exc_info=e)
            try:
                # Try with PulseAudio fallback
                os.environ['PULSE_SERVER'] = 'localhost'
                self.p = pyaudio.PyAudio()
            except Exception as e2:
                self.logger.error("Failed to reinitialize PyAudio with fallback", exc_info=e2)

    def toggle_mute(self) -> bool:
        """Toggle microphone mute state."""
        self.is_muted = not self.is_muted
        self.logger.info(f"Microphone {'muted' if self.is_muted else 'unmuted'}")
        return self.is_muted

    def get_audio_levels(self) -> Tuple[float, bool]:
        """Get current audio levels and speaking status."""
        return self.audio_processor.get_audio_level()

    def get_connection_state(self) -> ConnectionState:
        """Get current connection state."""
        return self.connection_mgr.state

    def get_last_error(self) -> Optional[str]:
        """Get last error message if any."""
        return self.connection_mgr.last_error

    def _signal_handler(self, signum: int, frame) -> None:
        """Handle system signals for graceful shutdown."""
        self.logger.info(f"Received signal {signum}, initiating graceful shutdown")
        self.stop_call()
