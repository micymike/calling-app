#!/usr/bin/env python3
"""
Debug version of the main app with additional error handling and logging.
"""

import sys
import traceback
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("debug.log"),
        logging.StreamHandler()
    ]
)

# Global exception handler
def exception_hook(exctype, value, tb):
    """
    Global exception handler to log unhandled exceptions
    """
    error_msg = ''.join(traceback.format_exception(exctype, value, tb))
    logging.critical(f"Unhandled exception: {error_msg}")
    sys.__excepthook__(exctype, value, tb)

sys.excepthook = exception_hook

# Import the app after setting up exception handling
try:
    from main import GirlfriendCallApp, QApplication
    
    if __name__ == "__main__":
        logging.info("Starting application in debug mode")
        app = QApplication(sys.argv)
        window = GirlfriendCallApp()
        window.show()
        sys.exit(app.exec_())
        
except Exception as e:
    logging.critical(f"Failed to start application: {e}")
    traceback.print_exc()