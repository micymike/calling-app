import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from typing import Optional


class CallLogger:
    """Handles application logging with both file and console output."""

    def __init__(self, log_file: str, log_level: int = logging.INFO):
        self.logger = logging.getLogger("GirlfriendCall")
        self.logger.setLevel(log_level)

        # Create logs directory if it doesn't exist
        log_dir = os.path.expanduser("~/.girlfriend_call/logs")
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, log_file)

        # Prevent duplicate handlers
        self.logger.handlers = []

        # File handler with rotation (max 5MB per file, keep 5 backup files)
        file_handler = RotatingFileHandler(
            log_path, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"  # 5 MB
        )
        file_handler.setLevel(log_level)
        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        console_formatter = logging.Formatter("%(levelname)s: %(message)s")
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)

        self.logger.info("Logging initialized")

    def debug(self, msg: str) -> None:
        """Log debug message."""
        self.logger.debug(msg)

    def info(self, msg: str) -> None:
        """Log info message."""
        self.logger.info(msg)

    def warning(self, msg: str) -> None:
        """Log warning message."""
        self.logger.warning(msg)

    def error(self, msg: str, exc_info: Optional[Exception] = None) -> None:
        """Log error message with optional exception info."""
        if exc_info:
            self.logger.error(msg, exc_info=True)
        else:
            self.logger.error(msg)

    def critical(self, msg: str, exc_info: Optional[Exception] = None) -> None:
        """Log critical message with optional exception info."""
        if exc_info:
            self.logger.critical(msg, exc_info=True)
        else:
            self.logger.critical(msg)

    @property
    def log_level(self) -> int:
        """Get current log level."""
        return self.logger.level

    @log_level.setter
    def log_level(self, level: int) -> None:
        """Set log level for both file and console handlers."""
        self.logger.setLevel(level)
        for handler in self.logger.handlers:
            handler.setLevel(level)

    def cleanup(self) -> None:
        """Clean up logging handlers."""
        for handler in self.logger.handlers:
            handler.close()
            self.logger.removeHandler(handler)
