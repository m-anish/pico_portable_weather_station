"""wifi_config.py
Manage WiFi credentials separate from static configuration.

WiFi settings are stored in wifi.json and can be safely reset by code
without risking corruption of the main settings.json configuration file.
"""

import json
import os

WIFI_FILE = "wifi.json"


def load_wifi_config():
    """Load WiFi configuration from file.
    
    Returns defaults with empty credentials if file is missing or corrupt.
    Empty credentials trigger the WiFi setup AP on boot.
    
    Returns:
        dict: WiFi config with ssid, password, retry_interval_s
    """
    try:
        if WIFI_FILE in os.listdir():
            with open(WIFI_FILE, "r") as f:
                return json.load(f)
    except Exception as e:
        print(f"WiFi config load error: {e}")
    
    # Return defaults (empty credentials trigger setup)
    return {
        "ssid": "",
        "password": "",
        "retry_interval_s": 60
    }


def save_wifi_config(wifi_cfg):
    """Save WiFi configuration to file with formatting.
    
    Args:
        wifi_cfg: Dictionary with ssid, password, retry_interval_s
    
    Returns:
        bool: True if save successful, False otherwise
    """
    try:
        with open(WIFI_FILE, "w") as f:
            json.dump(wifi_cfg, f, indent=2)
        return True
    except Exception as e:
        print(f"Failed to save WiFi config: {e}")
        return False


def reset_wifi():
    """Clear WiFi credentials to trigger setup on next boot.
    
    Returns:
        bool: True if reset successful, False otherwise
    """
    print("Resetting WiFi credentials...")
    return save_wifi_config({
        "ssid": "",
        "password": "",
        "retry_interval_s": 60
    })


def update_wifi(ssid, password, retry_interval_s=60):
    """Update WiFi credentials.
    
    Args:
        ssid: WiFi network name
        password: WiFi password
        retry_interval_s: Retry interval in seconds (default 60)
    
    Returns:
        bool: True if update successful, False otherwise
    """
    print(f"Updating WiFi config: SSID={ssid}")
    return save_wifi_config({
        "ssid": ssid,
        "password": password,
        "retry_interval_s": retry_interval_s
    })


def has_wifi_config():
    """Check if WiFi is configured (has non-empty SSID).
    
    Returns:
        bool: True if WiFi configured, False otherwise
    """
    wifi_cfg = load_wifi_config()
    return bool(wifi_cfg.get("ssid"))
