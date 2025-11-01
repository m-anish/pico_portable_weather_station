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
    "resetwifi": [1.0, 1.0],
}

# -------- REFRESH INTERVALS --------
REFRESH_INTERVALS = {
    "sht": 5,
    "pm": 10,
    "aqi": 10,
    "battery": 15,
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


def get_sleep_times(settings: dict):
    """Return (display_sleep_s, apc1_sleep_s) from settings with defaults.

    settings structure expects:
      {
        "power": {
          "display_sleep_s": <int>,  # seconds before display sleeps
          "apc1_sleep_s": <int>       # seconds before APC1 sleeps
        }
      }
    """
    power_cfg = (settings or {}).get("power", {})
    display_sleep = power_cfg.get("display_sleep_s", 30)
    apc1_sleep = power_cfg.get("apc1_sleep_s", 300)
    return display_sleep, apc1_sleep
