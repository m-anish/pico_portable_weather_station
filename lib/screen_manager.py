"""screen_manager.py
Screen manager for handling screen selection and rendering with caching.
"""

import time
from screens import available_screens, draw_screen
from config import REFRESH_INTERVALS


class ScreenManager:
    """Manages screen selection, refresh logic, and rendering.
    
    Coordinates between user input, cached sensor data, and display updates.
    Supports hierarchical menus for settings navigation.
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
        self.needs_redraw = False  # Flag to force immediate redraw
        
        # Initialize screen list (will update as sensors become available)
        self.screens = available_screens(cache)
        
        # Menu navigation state
        self.in_submenu = False
        self.submenu_type = None  # "settings" or "mode_select"
        self.submenu_index = 0
        self.menu_stack = []  # Track menu hierarchy for back navigation
    
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
            self.needs_redraw = True  # Force immediate redraw
            print(f"Screen: {self.get_current_screen_name()}")
    
    def prev_screen(self):
        """Switch to the previous screen."""
        if self.screens:
            self.screen_idx = (self.screen_idx - 1) % len(self.screens)
            self.needs_redraw = True  # Force immediate redraw
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
    
    def enter_settings_menu(self):
        """Enter the settings submenu."""
        self.in_submenu = True
        self.submenu_type = "settings"
        self.submenu_index = 0
        print("Entered settings menu")
    
    def enter_mode_selection(self):
        """Enter the mode selection submenu."""
        self.menu_stack.append(("settings", self.submenu_index))
        self.submenu_type = "mode_select"
        self.submenu_index = 0
        print("Entered mode selection")
    
    def enter_reset_confirmation(self):
        """Enter the reset WiFi confirmation submenu."""
        self.menu_stack.append(("settings", self.submenu_index))
        self.submenu_type = "reset_confirm"
        self.submenu_index = 0
        print("Entered reset WiFi confirmation")
    
    def enter_debug_menu(self):
        """Enter the debug submenu."""
        self.menu_stack.append(("settings", self.submenu_index))
        self.submenu_type = "debug"
        self.submenu_index = 0
        print("Entered debug menu")
    
    def exit_submenu(self):
        """Exit current submenu, return to previous level or main screens."""
        if self.menu_stack:
            # Return to previous menu level
            prev_type, prev_index = self.menu_stack.pop()
            self.submenu_type = prev_type
            self.submenu_index = prev_index
            print(f"Returned to {prev_type} menu")
        else:
            # Exit to main screens
            self.in_submenu = False
            self.submenu_type = None
            self.submenu_index = 0
            self.needs_redraw = True  # Force immediate redraw
            print("Exited to main screens")
    
    def next_menu_item(self):
        """Move to next item in current submenu."""
        if self.submenu_type == "settings":
            max_items = 4  # Reset WiFi, Select Mode, Debug, Back
        elif self.submenu_type == "mode_select":
            max_items = 3  # Station, Mobile, Back
        elif self.submenu_type == "reset_confirm":
            max_items = 3  # Yes, No, Back
        elif self.submenu_type == "debug":
            max_items = 2  # Exit Program, Back
        else:
            return
        
        self.submenu_index = (self.submenu_index + 1) % max_items
    
    def prev_menu_item(self):
        """Move to previous item in current submenu."""
        if self.submenu_type == "settings":
            max_items = 4  # Reset WiFi, Select Mode, Debug, Back
        elif self.submenu_type == "mode_select":
            max_items = 3  # Station, Mobile, Back
        elif self.submenu_type == "reset_confirm":
            max_items = 3  # Yes, No, Back
        elif self.submenu_type == "debug":
            max_items = 2  # Exit Program, Back
        else:
            return
        
        self.submenu_index = (self.submenu_index - 1) % max_items
    
    def handle_button(self):
        """Handle button press for current screen or menu.
        
        Returns:
            dict or None: Action dictionary with 'type' and optional 'data', or None
            Examples: 
                {"type": "reset_wifi"}
                {"type": "set_mode", "mode": "station"}
        """
        screen_name = self.get_current_screen_name()
        
        # Check if we're in settings screen (entry point)
        if screen_name == "settings" and not self.in_submenu:
            self.enter_settings_menu()
            return None
        
        # Handle menu navigation
        if self.in_submenu:
            if self.submenu_type == "settings":
                # Settings menu: Reset WiFi, Select Mode, Debug, Back
                if self.submenu_index == 0:
                    # Reset WiFi selected - show confirmation
                    self.enter_reset_confirmation()
                    return None
                elif self.submenu_index == 1:
                    # Select Mode selected
                    self.enter_mode_selection()
                    return None
                elif self.submenu_index == 2:
                    # Debug selected
                    self.enter_debug_menu()
                    return None
                elif self.submenu_index == 3:
                    # Back selected
                    self.exit_submenu()
                    return None
            
            elif self.submenu_type == "reset_confirm":
                # Reset WiFi confirmation: Yes, No, Back
                if self.submenu_index == 0:
                    # Yes - confirm reset
                    self.exit_submenu()  # Return to settings menu
                    self.exit_submenu()  # Return to main screens
                    return {"type": "reset_wifi"}
                elif self.submenu_index == 1 or self.submenu_index == 2:
                    # No or Back - cancel reset
                    self.exit_submenu()  # Return to settings menu
                    return None
            
            elif self.submenu_type == "mode_select":
                # Mode selection: Station, Mobile, Back
                if self.submenu_index == 0:
                    # Station mode selected
                    self.exit_submenu()  # Return to settings menu
                    self.exit_submenu()  # Return to main screens
                    return {"type": "set_mode", "mode": "station"}
                elif self.submenu_index == 1:
                    # Mobile mode selected
                    self.exit_submenu()  # Return to settings menu
                    self.exit_submenu()  # Return to main screens
                    return {"type": "set_mode", "mode": "mobile"}
                elif self.submenu_index == 2:
                    # Back selected
                    self.exit_submenu()  # Return to settings menu
                    return None
            
            elif self.submenu_type == "debug":
                # Debug menu: Exit Program, Back
                if self.submenu_index == 0:
                    # Exit Program selected
                    return {"type": "exit_program"}
                elif self.submenu_index == 1:
                    # Back selected
                    self.exit_submenu()  # Return to settings menu
                    return None
        
        # Legacy resetwifi screen support (if still present)
        if screen_name == "resetwifi":
            return {"type": "reset_wifi"}
        
        return None
