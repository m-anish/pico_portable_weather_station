"""Lightweight logging library for MicroPython with USB detection.

Features:
- Log levels: DEBUG, INFO, WARN, ERROR
- USB detection (checks if connected to Thonny/REPL)
- Conditional output based on USB status:
  - USB connected: All levels to console
  - USB not connected: DEBUG/INFO suppressed, WARN/ERROR to file only
- Log file: sys.log with 100KB size limit (deleted when exceeded)
"""

import sys
import os

# Log levels
DEBUG = 10
INFO = 20
WARN = 30
ERROR = 40

# Log file configuration
LOG_FILE = "sys.log"
MAX_LOG_SIZE = 102400  # 100KB in bytes

# Global log level (can be changed at runtime)
_log_level = INFO

def set_level(level):
    """Set the global log level.
    
    Args:
        level: One of DEBUG, INFO, WARN, ERROR
    """
    global _log_level
    _log_level = level

def is_usb_connected():
    """Check if USB/REPL is connected.
    
    Returns:
        bool: True if USB connected (REPL active), False otherwise
    """
    try:
        # Check if stdin has a read method (indicates REPL is active)
        return hasattr(sys.stdin, 'read')
    except:
        return False

def _get_log_size():
    """Get current log file size in bytes.
    
    Returns:
        int: File size in bytes, or 0 if file doesn't exist
    """
    try:
        stat = os.stat(LOG_FILE)
        return stat[6]  # Size is at index 6 in stat tuple
    except OSError:
        return 0

def _rotate_log():
    """Rotate log file by deleting it when it exceeds MAX_LOG_SIZE."""
    try:
        size = _get_log_size()
        if size >= MAX_LOG_SIZE:
            os.remove(LOG_FILE)
    except OSError:
        pass  # File doesn't exist or can't be deleted

def _write_to_file(message):
    """Write message to log file.
    
    Args:
        message: String message to write
    """
    try:
        # Check if rotation is needed
        _rotate_log()
        
        # Append to log file
        with open(LOG_FILE, 'a') as f:
            f.write(message + '\n')
    except Exception as e:
        # Can't log to file, silently fail
        # (avoid infinite recursion if logging fails)
        pass

def _format_message(level_name, message):
    """Format log message with level prefix.
    
    Args:
        level_name: String name of log level
        message: Message to format
        
    Returns:
        str: Formatted message
    """
    return f"[{level_name}] {message}"

def _log(level, level_name, message):
    """Internal logging function.
    
    Args:
        level: Numeric log level
        level_name: String name of log level
        message: Message to log
    """
    # Check if message should be logged based on level
    if level < _log_level:
        return
    
    usb_connected = is_usb_connected()
    formatted = _format_message(level_name, message)
    
    if usb_connected:
        # USB connected: All levels go to console
        print(formatted)
    else:
        # USB not connected
        if level >= WARN:
            # WARN/ERROR: Write to file only
            _write_to_file(formatted)
        # DEBUG/INFO: Suppressed when USB not connected

def debug(message):
    """Log debug message.
    
    Args:
        message: Message to log
    """
    _log(DEBUG, "DEBUG", message)

def info(message):
    """Log info message.
    
    Args:
        message: Message to log
    """
    _log(INFO, "INFO", message)

def warn(message):
    """Log warning message.
    
    Args:
        message: Message to log
    """
    _log(WARN, "WARN", message)

def error(message):
    """Log error message.
    
    Args:
        message: Message to log
    """
    _log(ERROR, "ERROR", message)

def clear_log():
    """Clear the log file."""
    try:
        os.remove(LOG_FILE)
    except OSError:
        pass

def get_log_contents():
    """Get the contents of the log file.
    
    Returns:
        str: Log file contents, or empty string if file doesn't exist
    """
    try:
        with open(LOG_FILE, 'r') as f:
            return f.read()
    except OSError:
        return ""

def get_log_stats():
    """Get log file statistics.
    
    Returns:
        dict: Dictionary with 'size' (bytes) and 'max_size' (bytes)
    """
    return {
        'size': _get_log_size(),
        'max_size': MAX_LOG_SIZE,
        'usb_connected': is_usb_connected()
    }
