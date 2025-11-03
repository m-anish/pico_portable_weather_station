"""runtime_state.py
Manage runtime state (mode selection, etc.) separate from static config.

Runtime state is stored in runtime.json and can be safely modified by code
without risking corruption of the main settings.json configuration file.
"""

import json
import os

RUNTIME_FILE = "runtime.json"


def load_runtime_state():
    """Load runtime state from file.
    
    Returns defaults if file is missing or corrupt. This ensures the system
    always has a valid runtime state to work with.
    
    Returns:
        dict: Runtime state with at least {"mode": None}
    """
    try:
        if RUNTIME_FILE in os.listdir():
            with open(RUNTIME_FILE, "r") as f:
                return json.load(f)
    except Exception as e:
        print(f"Runtime state load error: {e}")
    
    # Return defaults
    return {"mode": None}


def save_runtime_state(state):
    """Save runtime state to file.
    
    Args:
        state: Dictionary with runtime state
    
    Returns:
        bool: True if save successful, False otherwise
    """
    try:
        with open(RUNTIME_FILE, "w") as f:
            json.dump(state, f)
        return True
    except Exception as e:
        print(f"Failed to save runtime state: {e}")
        return False


def get_current_mode(default="mobile"):
    """Get current operating mode from runtime state.
    
    Args:
        default: Default mode if not set in runtime state
    
    Returns:
        str: Current mode ("station" or "mobile")
    """
    state = load_runtime_state()
    mode = state.get("mode")
    return mode if mode else default


def set_mode(mode):
    """Set operating mode in runtime state.
    
    Args:
        mode: Operating mode ("station" or "mobile")
    
    Returns:
        bool: True if save successful, False otherwise
    """
    state = load_runtime_state()
    state["mode"] = mode
    return save_runtime_state(state)
