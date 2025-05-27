import socket
import requests


def get_local_ip():
    """Attempts to find the local IP address of the machine."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Connect to an arbitrary address (doesn't send data) to get the local IP
        # that would be used for outbound connections.
        s.connect(("10.255.255.255", 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = "127.0.0.1"  # Fallback to localhost if unable to determine
    finally:
        s.close()
    return IP


def get_public_ip():
    """
    Attempts to get the public IP address using an external API service.
    This requires an internet connection.
    """
    try:
        response = requests.get("https://api.ipify.org").text
        return response
    except Exception:
        return "Failed to fetch (check internet connection)"
