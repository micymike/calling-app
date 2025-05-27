import os
import json
import logging
from dataclasses import dataclass
from typing import Optional


@dataclass
class AudioConfig:
    """Audio stream configuration."""

    chunk_size: int = 1024
    sample_rate: int = 44100
    channels: int = 1
    format_size: int = 16  # 16-bit audio
    buffer_size: int = 4096  # Larger buffer for network jitter


@dataclass
class NetworkConfig:
    """Network configuration."""

    port: int = 5000
    timeout: float = 1.0  # Increased timeout for better reliability
    reconnect_attempts: int = 5  # More reconnection attempts
    reconnect_delay: float = 2.0  # Longer delay between reconnection attempts
    heartbeat_interval: float = 2.0  # Less frequent heartbeats to reduce network traffic


@dataclass
class Config:
    """Application configuration."""

    audio: AudioConfig = None
    network: NetworkConfig = None
    log_level: int = logging.INFO
    log_file: str = "girlfriend_call.log"
    save_settings: bool = True
    last_called_ip: Optional[str] = None
    last_called_number: Optional[str] = None
    number_server: str = "127.0.0.1"
    number_server_port: int = 5001
    user_number: Optional[str] = None
    
    def __post_init__(self):
        if self.audio is None:
            self.audio = AudioConfig()
        if self.network is None:
            self.network = NetworkConfig()

    def save(self) -> None:
        """Save configuration to a JSON file."""
        if not self.save_settings:
            return

        config_dir = os.path.expanduser("~/.girlfriend_call")
        os.makedirs(config_dir, exist_ok=True)
        config_path = os.path.join(config_dir, "config.json")

        # Convert dataclasses to dict
        config_dict = {
            "audio": {
                "chunk_size": self.audio.chunk_size,
                "sample_rate": self.audio.sample_rate,
                "channels": self.audio.channels,
                "format_size": self.audio.format_size,
                "buffer_size": self.audio.buffer_size,
            },
            "network": {
                "port": self.network.port,
                "timeout": self.network.timeout,
                "reconnect_attempts": self.network.reconnect_attempts,
                "reconnect_delay": self.network.reconnect_delay,
                "heartbeat_interval": self.network.heartbeat_interval,
            },
            "log_level": self.log_level,
            "log_file": self.log_file,
            "save_settings": self.save_settings,
            "last_called_ip": self.last_called_ip,
        }

        with open(config_path, "w") as f:
            json.dump(config_dict, f, indent=4)

    @classmethod
    def load(cls) -> "Config":
        """Load configuration from a JSON file or return defaults."""
        config_path = os.path.expanduser("~/.girlfriend_call/config.json")

        if not os.path.exists(config_path):
            return cls()

        try:
            with open(config_path, "r") as f:
                config_dict = json.load(f)

            audio_config = AudioConfig(**config_dict.get("audio", {}))
            network_config = NetworkConfig(**config_dict.get("network", {}))

            return cls(
                audio=audio_config,
                network=network_config,
                log_level=config_dict.get("log_level", logging.INFO),
                log_file=config_dict.get("log_file", "girlfriend_call.log"),
                save_settings=config_dict.get("save_settings", True),
                last_called_ip=config_dict.get("last_called_ip"),
            )
        except Exception as e:
            logging.warning(f"Failed to load config: {e}. Using defaults.")
            return cls()
