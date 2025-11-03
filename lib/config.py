# config.py
# Centralized configuration and settings helpers for the weather station

import json
import os

SETTINGS_FILE = "settings.json"

# -------- FONT SCALE SETTINGS --------
FONT_SCALES = {
    "temp_hum": [3, 3],
    "pm": [1, 2, 2, 2],
    "aqi": [2, 1],
    "battery": [3, 3],
    "settings": [1.0, 1.0],  # Settings menu (was "resetwifi")
}

# -------- REFRESH INTERVALS --------
REFRESH_INTERVALS = {
    "sht": 5,
    "pm": 10,
    "gases": 10,
    "aqi": 10,
    "sysinfo": 15,
    "scroll": 0,  # Scroll screen updates via step_scroll_screen()
    "resetwifi": 0,
}

def load_settings():
    """Load settings from SETTINGS_FILE, with safe defaults."""
    if SETTINGS_FILE in os.listdir():
        try:
            with open(SETTINGS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "i2c": {"sda": 16, "scl": 17},
        "power": {
            "display_sleep_s": 30,
            "apc1_sleep_s": 300
        }
    }


# -------- APC1 PIN DEFAULTS AND HELPERS --------
# Per README wiring: SET -> GP22, RST -> GP21
APC1_SET_DEFAULT_PIN = 22
APC1_RESET_DEFAULT_PIN = 21


def get_apc1_pins(settings: dict):
    """Return (set_pin, reset_pin) using settings if present, else defaults.

    settings structure expects:
      {
        "apc1": {
          "set_pin": <int>,
          "reset_pin": <int>
        }
      }
    """
    apc1_cfg = (settings or {}).get("apc1", {})
    set_pin = apc1_cfg.get("set_pin", APC1_SET_DEFAULT_PIN)
    reset_pin = apc1_cfg.get("reset_pin", APC1_RESET_DEFAULT_PIN)
    return set_pin, reset_pin


def get_screen_timeout():
    """Return screen timeout from runtime state.
    
    Returns timeout in seconds for both display and APC1 sleep (in mobile mode).
    In station mode, APC1 follows its own cycle schedule.
    
    Returns:
        int: Timeout in seconds (0 means "Never")
    """
    from runtime_state import get_screen_timeout
    return get_screen_timeout(default=30)


def get_sensor_intervals(settings: dict):
    """Return sensor read intervals from settings with defaults.
    
    settings structure expects:
      {
        "sensors": {
          "shtc3_interval_s": <int>,   # SHTC3 read interval in seconds
          "apc1_interval_s": <int>,    # APC1 read interval in seconds
          "battery_interval_s": <int>  # Battery read interval in seconds
        }
      }
    
    Returns:
        tuple: (shtc3_interval, apc1_interval, battery_interval) in seconds
    """
    sensor_cfg = (settings or {}).get("sensors", {})
    shtc3_interval = sensor_cfg.get("shtc3_interval_s", 5)
    apc1_interval = sensor_cfg.get("apc1_interval_s", 10)
    battery_interval = sensor_cfg.get("battery_interval_s", 15)
    return shtc3_interval, apc1_interval, battery_interval


def get_display_settings(settings: dict):
    """Return display update settings from settings with defaults.
    
    settings structure expects:
      {
        "display": {
          "refresh_fps": <int>,    # Display refresh rate in frames per second
          "input_poll_hz": <int>   # Input polling rate in Hz
        }
      }
    
    Returns:
        tuple: (refresh_fps, input_poll_hz)
    """
    display_cfg = (settings or {}).get("display", {})
    refresh_fps = display_cfg.get("refresh_fps", 20)
    input_poll_hz = display_cfg.get("input_poll_hz", 50)
    return refresh_fps, input_poll_hz


def get_blynk_settings(settings: dict):
    """Return Blynk MQTT settings from settings with defaults.
    
    settings structure expects:
      {
        "blynk": {
          "enabled": <bool>,                # Enable/disable Blynk integration
          "template_id": <str>,             # Blynk template ID
          "template_name": <str>,           # Blynk template name
          "auth_token": <str>,              # Blynk authentication token
          "mqtt_broker": <str>,             # MQTT broker address
          "mqtt_update_interval_s": <int>   # Data publish interval in seconds
        }
      }
    
    Returns:
        dict: Blynk configuration dictionary
    """
    blynk_cfg = (settings or {}).get("blynk", {})
    return {
        "enabled": blynk_cfg.get("enabled", False),
        "template_id": blynk_cfg.get("template_id", ""),
        "template_name": blynk_cfg.get("template_name", ""),
        "auth_token": blynk_cfg.get("auth_token", ""),
        "mqtt_broker": blynk_cfg.get("mqtt_broker", "blynk.cloud"),
        "mqtt_update_interval_s": blynk_cfg.get("mqtt_update_interval_s", 30)
    }


def get_ntp_settings(settings: dict):
    """Return NTP time synchronization settings from settings with defaults.
    
    settings structure expects:
      {
        "ntp": {
          "enabled": <bool>,                # Enable/disable NTP sync
          "servers": <list>,                # List of NTP server hostnames
          "timezone_offset_hours": <float>, # Timezone offset in hours (e.g., 5.5 for IST)
          "sync_interval_s": <int>          # Re-sync interval in seconds
        }
      }
    
    Returns:
        dict: NTP configuration dictionary
    """
    ntp_cfg = (settings or {}).get("ntp", {})
    return {
        "enabled": ntp_cfg.get("enabled", True),
        "servers": ntp_cfg.get("servers", ["pool.ntp.org"]),
        "timezone_offset_hours": ntp_cfg.get("timezone_offset_hours", 0.0),
        "sync_interval_s": ntp_cfg.get("sync_interval_s", 3600)
    }


def get_wifi_settings(settings: dict):
    """Return WiFi connection settings from wifi.json only.
    
    Reads WiFi credentials exclusively from wifi.json. If the file doesn't exist
    or has empty credentials, returns empty dict which triggers AP mode in boot.py.
    
    Args:
        settings: Settings dictionary (unused, kept for API compatibility)
    
    Returns:
        dict: WiFi configuration with ssid, password, retry_interval_s
    """
    from wifi_config import load_wifi_config
    
    # Read from wifi.json only - no fallback
    return load_wifi_config()


def get_operation_mode(settings: dict):
    """Return operation mode from runtime.json with fallback to settings.
    
    Reads current mode from runtime.json (set via UI). Falls back to
    "default_mode" field in settings.json, or hardcoded "mobile" default.
    
    Args:
        settings: Settings dictionary (used for default_mode fallback)
    
    Returns:
        str: Operation mode ("station" or "mobile")
    """
    from runtime_state import get_current_mode
    
    # Get default from settings.json (or "mobile" if not present)
    default = (settings or {}).get("default_mode", "mobile")
    
    # Get current mode from runtime.json (or use default)
    return get_current_mode(default)


def get_station_mode_settings(settings: dict):
    """Return station mode APC1 power cycling settings.
    
    settings structure expects:
      {
        "station_mode": {
          "cycle_period_s": <int>,    # Time between APC1 wake cycles in seconds
          "warmup_time_s": <int>,     # Time to wait after waking APC1 before reading
          "read_delay_ms": <int>      # Delay before putting APC1 back to sleep
        }
      }
    
    Returns:
        dict: Station mode configuration dictionary
    """
    station_cfg = (settings or {}).get("station_mode", {})
    return {
        "cycle_period_s": station_cfg.get("cycle_period_s", 300),     # 5 minutes
        "warmup_time_s": station_cfg.get("warmup_time_s", 60),        # 1 minute
        "read_delay_ms": station_cfg.get("read_delay_ms", 100)        # 100ms
    }
