import sys
import threading
import socket
import os
from typing import Optional

from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QMessageBox,
    QProgressBar,
    QFrame,
    QCheckBox,
    QSystemTrayIcon,
    QMenu,
    QStyle,
)
from PyQt5.QtCore import QTimer, Qt, pyqtSignal
from PyQt5.QtGui import QIcon, QPalette, QColor

from config import Config
from call_manager import CallManager
from number_service import NumberService
from ringtone import RingtonePlayer
from utils import get_local_ip, get_public_ip


class AudioLevelBar(QProgressBar):
    """Custom progress bar for displaying audio levels."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimum(0)
        self.setMaximum(100)
        self.setValue(0)
        self.setTextVisible(False)
        self.setMaximumHeight(10)

    def update_level(self, level: float):
        """Update the audio level display (0.0 to 1.0)."""
        self.setValue(int(level * 100))


class StatusIndicator(QFrame):
    """Custom widget for displaying connection status."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(12, 12)
        self.status = "disconnected"

    def set_status(self, status: str):
        """Update the status indicator color based on connection state."""
        self.status = status
        colors = {
            "disconnected": "#ff0000",  # Red
            "connecting": "#ffa500",  # Orange
            "connected": "#00ff00",  # Green
            "failed": "#ff0000",  # Red
        }
        self.setStyleSheet(
            f"background-color: {colors.get(status, '#808080')}; "
            "border-radius: 6px; border: 1px solid #404040;"
        )


class GirlfriendCallApp(QWidget):
    """Main application window."""

    def __init__(self):
        super().__init__()

        # Load configuration
        self.config = Config.load()

        # Initialize number service
        self.number_service = NumberService(
            server_host=self.config.number_server,
            server_port=self.config.number_server_port
        )
        
        # Initialize call manager with config
        self.call_manager = CallManager(self.config)
        
        # Initialize ringtone player
        self.ringtone_player = RingtonePlayer()

        # Set up UI
        self.init_ui()

        # Create system tray icon
        self.setup_tray_icon()

        # Start monitoring audio levels
        self.start_audio_monitoring()
        
        # Register user number
        self.register_user_number()

    def setup_theme(self):
        """Set up the application theme."""
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(53, 53, 53))
        palette.setColor(QPalette.WindowText, QColor(255, 255, 255))
        palette.setColor(QPalette.Base, QColor(25, 25, 25))
        palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
        palette.setColor(QPalette.Text, QColor(255, 255, 255))
        palette.setColor(QPalette.Button, QColor(53, 53, 53))
        palette.setColor(QPalette.ButtonText, QColor(255, 255, 255))
        self.setPalette(palette)

    def init_ui(self):
        """Initialize the graphical user interface."""
        self.setWindowTitle("GirlfriendCall")
        self.setGeometry(100, 100, 450, 300)
        self.setup_theme()

        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)

        # Status bar at the top
        status_bar = QHBoxLayout()
        self.status_indicator = StatusIndicator()
        self.status_indicator.set_status("disconnected")
        status_bar.addWidget(self.status_indicator)
        self.status_label = QLabel("Ready to call")
        status_bar.addWidget(self.status_label)
        status_bar.addStretch()
        main_layout.addLayout(status_bar)

        # IP and Number Information Section
        ip_info = QFrame()
        ip_info.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        ip_info_layout = QVBoxLayout()

        # User Number
        self.user_number_label = QLabel("Your Number: <i>Registering...</i>")
        self.user_number_label.setTextFormat(Qt.RichText)
        ip_info_layout.addWidget(self.user_number_label)
        
        # Local IP
        local_ip = get_local_ip()
        self.local_ip_label = QLabel(f"Your Local IP: <b>{local_ip}</b>")
        self.local_ip_label.setTextFormat(Qt.RichText)
        ip_info_layout.addWidget(self.local_ip_label)

        # Public IP
        self.public_ip_label = QLabel("Your Public IP: <i>Fetching...</i>")
        self.public_ip_label.setTextFormat(Qt.RichText)
        ip_info_layout.addWidget(self.public_ip_label)

        ip_info.setLayout(ip_info_layout)
        main_layout.addWidget(ip_info)

        # Target Input
        input_frame = QFrame()
        input_frame.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        input_layout = QVBoxLayout()

        # Number input
        target_number_layout = QHBoxLayout()
        target_number_layout.addWidget(QLabel("Call Number:"))
        self.target_number_input = QLineEdit()
        self.target_number_input.setPlaceholderText("Enter 4-digit number to call")
        self.target_number_input.setMaxLength(4)
        
        # Load last called number if available
        if self.config.last_called_number:
            self.target_number_input.setText(self.config.last_called_number)
            
        target_number_layout.addWidget(self.target_number_input)
        input_layout.addLayout(target_number_layout)

        # Remember settings checkbox
        self.remember_settings = QCheckBox("Remember last called number")
        self.remember_settings.setChecked(self.config.save_settings)
        input_layout.addWidget(self.remember_settings)

        input_frame.setLayout(input_layout)
        main_layout.addWidget(input_frame)

        # Audio Levels
        levels_frame = QFrame()
        levels_frame.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        levels_layout = QVBoxLayout()

        # Input level
        input_level_layout = QHBoxLayout()
        input_level_layout.addWidget(QLabel("Input:"))
        self.input_level = AudioLevelBar()
        input_level_layout.addWidget(self.input_level)
        levels_layout.addLayout(input_level_layout)

        # Output level
        output_level_layout = QHBoxLayout()
        output_level_layout.addWidget(QLabel("Output:"))
        self.output_level = AudioLevelBar()
        output_level_layout.addWidget(self.output_level)
        levels_layout.addLayout(output_level_layout)

        levels_frame.setLayout(levels_layout)
        main_layout.addWidget(levels_frame)

        # Controls
        controls_layout = QHBoxLayout()

        # Call button
        self.call_button = QPushButton("Call")
        self.call_button.clicked.connect(self.start_call)
        controls_layout.addWidget(self.call_button)

        # Hang up button
        self.hangup_button = QPushButton("Hang Up")
        self.hangup_button.clicked.connect(self.stop_call)
        self.hangup_button.setEnabled(False)
        controls_layout.addWidget(self.hangup_button)

        # Mute button
        self.mute_button = QPushButton("Mute")
        self.mute_button.setCheckable(True)
        self.mute_button.clicked.connect(self.toggle_mute)
        self.mute_button.setEnabled(False)
        controls_layout.addWidget(self.mute_button)

        main_layout.addLayout(controls_layout)

        self.setLayout(main_layout)

    def setup_tray_icon(self):
        """Set up system tray icon with menu."""
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.style().standardIcon(QStyle.SP_ComputerIcon))

        # Create tray menu
        tray_menu = QMenu()
        show_action = tray_menu.addAction("Show")
        show_action.triggered.connect(self.show)
        quit_action = tray_menu.addAction("Quit")
        quit_action.triggered.connect(self.quit_application)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()

    def start_audio_monitoring(self):
        """Start monitoring audio levels."""
        self.audio_timer = QTimer(self)
        self.audio_timer.timeout.connect(self.update_audio_levels)
        self.audio_timer.start(100)  # Update every 100ms

    def update_audio_levels(self):
        """Update audio level indicators."""
        if self.call_manager.is_calling:
            level, speaking = self.call_manager.get_audio_levels()
            self.input_level.update_level(level)
        else:
            self.input_level.update_level(0)
            self.output_level.update_level(0)

    def fetch_public_ip(self):
        """Fetch public IP address asynchronously."""

        def _fetch():
            public_ip = get_public_ip()
            self.public_ip_label.setText(f"Your Public IP: <b>{public_ip}</b>")
            
            # Update heartbeat with public IP if available
            if hasattr(self, 'number_service') and self.number_service.user_number:
                self.number_service.start_heartbeat(public_ip)

        threading.Thread(target=_fetch, daemon=True).start()

    def register_user_number(self):
        """Register and get a user number."""
        def _register():
            try:
                number = self.number_service.register_user()
                self.config.user_number = number
                self.config.save()
                
                # Update UI with the number
                self.user_number_label.setText(f"Your Number: <b>{number}</b>")
                
                # Start heartbeat to keep number registration active
                local_ip = get_local_ip()
                self.number_service.start_heartbeat(local_ip)
                
            except Exception as e:
                self.user_number_label.setText("Number registration failed")
                print(f"Error registering number: {e}")
                
        threading.Thread(target=_register, daemon=True).start()
        
    def start_call(self):
        """Start a call to the specified number."""
        target_number = self.target_number_input.text().strip()
        
        # Check if number is provided
        if not target_number:
            QMessageBox.warning(self, "Input Error", "Please enter a 4-digit number to call.")
            return
            
        # Validate number format
        if not target_number.isdigit() or len(target_number) != 4:
            QMessageBox.warning(self, "Input Error", "Please enter a valid 4-digit number.")
            return
            
        self.status_label.setText(f"Looking up number {target_number}...")
        
        def _lookup_and_call():
            try:
                ip_address = self.number_service.lookup_number(target_number)
                if ip_address:
                    self._initiate_call(ip_address, target_number)
                    
                    # Save the number if remember is checked
                    if self.remember_settings.isChecked():
                        self.config.last_called_number = target_number
                        self.config.save()
                else:
                    self.handle_call_error(f"Number {target_number} not found or offline")
            except Exception as e:
                self.handle_call_error(str(e))
                
        threading.Thread(target=_lookup_and_call, daemon=True).start()
            
    def _initiate_call(self, target_ip, target_number):
        """Initiate the call to the specified IP."""
        self.status_indicator.set_status("connecting")
        self.status_label.setText(f"Connecting to {target_number}...")
        self.call_button.setEnabled(False)
        self.hangup_button.setEnabled(True)
        self.mute_button.setEnabled(True)
        
        # Play ringtone while connecting
        self.ringtone_player.play_ringtone()

        try:
            threading.Thread(
                target=self._start_call_thread, args=(target_ip, target_number), daemon=True
            ).start()
        except Exception as e:
            self.ringtone_player.stop_ringtone()
            self.handle_call_error(str(e))

    def _start_call_thread(self, target_ip: str, target_number: str):
        """Handle call initialization in a separate thread."""
        try:
            # Add more detailed logging
            print(f"Starting call to IP: {target_ip}, Number: {target_number}")
            
            self.call_manager.start_call(target_ip)
            
            # Stop ringtone when connected
            self.ringtone_player.stop_ringtone()
            
            self.status_indicator.set_status("connected")
            self.status_label.setText(f"Connected to {target_number}")

            # Save settings if enabled
            if self.remember_settings.isChecked():
                self.config.last_called_number = target_number
                self.config.save_settings = True
                self.config.save()

        except Exception as e:
            # Stop ringtone if call fails
            self.ringtone_player.stop_ringtone()
            
            import traceback
            error_details = traceback.format_exc()
            print(f"Call error: {e}")
            print(f"Error details: {error_details}")
            self.handle_call_error(f"{str(e)}\n\nDetails: {error_details}")

    def handle_call_error(self, error_msg: str):
        """Handle call-related errors."""
        # Make sure we're running in the main thread for UI updates
        if threading.current_thread() is not threading.main_thread():
            # Use Qt's signal/slot mechanism to safely update UI from another thread
            from PyQt5.QtCore import QMetaObject, Qt, Q_ARG
            QMetaObject.invokeMethod(
                self, 
                "_handle_call_error_main_thread",
                Qt.QueuedConnection, 
                Q_ARG(str, error_msg)
            )
            return
            
        self._handle_call_error_main_thread(error_msg)
        
    def _handle_call_error_main_thread(self, error_msg: str):
        """Handle call errors in the main thread."""
        print(f"Handling call error in main thread: {error_msg}")
        self.status_indicator.set_status("failed")
        self.status_label.setText("Call failed")
        self.call_button.setEnabled(True)
        self.hangup_button.setEnabled(False)
        self.mute_button.setEnabled(False)
        QMessageBox.critical(self, "Call Error", f"Failed to start call: {error_msg}")

    def stop_call(self):
        """Stop the current call."""
        self.status_label.setText("Hanging up...")
        
        # Make sure ringtone is stopped
        self.ringtone_player.stop_ringtone()
        
        self.call_manager.stop_call()
        self.status_indicator.set_status("disconnected")
        self.status_label.setText("Ready to call")
        self.call_button.setEnabled(True)
        self.hangup_button.setEnabled(False)
        self.mute_button.setEnabled(False)
        self.mute_button.setChecked(False)

    def toggle_mute(self, checked: bool):
        """Toggle microphone mute state."""
        if self.call_manager.toggle_mute():
            self.mute_button.setText("Unmute")
        else:
            self.mute_button.setText("Mute")

    def quit_application(self):
        """Clean up and quit the application."""
        self.call_manager.stop_call()
        if hasattr(self, 'number_service'):
            self.number_service.stop_heartbeat()
        if hasattr(self, 'ringtone_player'):
            self.ringtone_player.stop_ringtone()
        QApplication.quit()

    def closeEvent(self, event):
        """Handle window close event."""
        if self.call_manager.is_calling:
            self.call_manager.stop_call()
        if hasattr(self, 'number_service'):
            self.number_service.stop_heartbeat()
        if hasattr(self, 'ringtone_player'):
            self.ringtone_player.stop_ringtone()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = GirlfriendCallApp()
    window.show()
    sys.exit(app.exec_())
