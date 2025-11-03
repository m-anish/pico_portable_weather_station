"""screen_manager.py
Screen manager for handling screen selection and rendering with caching.
"""

import time
from screens import available_screens, draw_screen
from config import REFRESH_INTERVALS


class ScreenManager:
    """Manages screen selection, refresh logic, and rendering.
    
    Coordinates between user input, cached sensor data, and display updates.
    """
    
    def __init__(self, cache, font_scales):
        """Initialize screen manager.
        
        Args:
            cache: SensorCache instance
            font_scales: Dictionary of font scales for legacy compatibility
        """
        self.cache = cache
        self.font_scales = font_scales
        self.screen_idx = 0
        self.last_refresh = 0
        
        # Initialize screen list (will update as sensors become available)
        self.screens = available_screens(cache)
    
    def update_available_screens(self):
        """Update the list of available screens based on current sensor data."""
        old_count = len(self.screens)
        self.screens = available_screens(self.cache)
        
        # Clamp current index if screen count changed
        if self.screen_idx >= len(self.screens):
            self.screen_idx = len(self.screens) - 1
        
        # Log if screens changed
        if len(self.screens) != old_count:
            print(f"Available screens updated: {len(self.screens)} screens")
    
    def get_current_screen_name(self):
        """Get the name/ID of the current screen."""
        if self.screens:
            return self.screens[self.screen_idx][0]
        return "resetwifi"  # Fallback
    
    def next_screen(self):
        """Switch to the next screen."""
        if self.screens:
            self.screen_idx = (self.screen_idx + 1) % len(self.screens)
            self.last_refresh = 0  # Force immediate refresh
            print(f"Screen: {self.get_current_screen_name()}")
    
    def prev_screen(self):
        """Switch to the previous screen."""
        if self.screens:
            self.screen_idx = (self.screen_idx - 1) % len(self.screens)
            self.last_refresh = 0  # Force immediate refresh
            print(f"Screen: {self.get_current_screen_name()}")
    
    def should_refresh(self):
        """Check if current screen should be refreshed based on interval."""
        screen_name = self.get_current_screen_name()
        interval = REFRESH_INTERVALS.get(screen_name, 0)
        
        if interval <= 0:
            return False  # No automatic refresh
        
        now = time.time()
        return (now - self.last_refresh) > interval
    
    def mark_refreshed(self):
        """Mark that the screen was just refreshed."""
        self.last_refresh = time.time()
    
    def draw_screen(self, cache, oled):
        """Draw the current screen to the display using cached data.
        
        Args:
            cache: SensorCache instance (for convenience, though self.cache exists)
            oled: SSD1306 display instance
        """
        screen_name = self.get_current_screen_name()
        draw_screen(screen_name, oled, cache, self.font_scales)
    
    def handle_button(self):
        """Handle button press for current screen.
        
        Returns:
            str or None: Action to take (e.g., "resetwifi") or None
        """
        screen_name = self.get_current_screen_name()
        
        if screen_name == "resetwifi":
            return "resetwifi"
        
        return None
