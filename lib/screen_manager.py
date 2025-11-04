"""screen_manager.py
Screen manager for handling screen selection and rendering with caching.
"""

import time
from screens import available_screens, draw_screen
from config import REFRESH_INTERVALS
import logger


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
        self.scroll_offset = 0  # For scrollable menus
        self.menu_stack = []  # Track menu hierarchy for back navigation
        
        # Display timeout state
        self.display_timeout_mode = "adjusting"  # "adjusting" or "confirming"
        self.timeout_confirm_index = 0  # 0=Save, 1=Cancel
        self.original_timeout_value = None  # Store original value for cancel
    
    def update_available_screens(self):
        """Update the list of available screens based on current sensor data."""
        old_count = len(self.screens)
        self.screens = available_screens(self.cache)
        
        # Clamp current index if screen count changed
        if self.screen_idx >= len(self.screens):
            self.screen_idx = len(self.screens) - 1
        
        # Log if screens changed
        if len(self.screens) != old_count:
            logger.info(f"Available screens updated: {len(self.screens)} screens")
    
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
            logger.debug(f"Screen: {self.get_current_screen_name()}")
    
    def prev_screen(self):
        """Switch to the previous screen."""
        if self.screens:
            self.screen_idx = (self.screen_idx - 1) % len(self.screens)
            self.needs_redraw = True  # Force immediate redraw
            logger.debug(f"Screen: {self.get_current_screen_name()}")

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
        logger.debug("Entered settings menu")

    def enter_mode_selection(self):
        """Enter the mode selection submenu."""
        self.menu_stack.append(("settings", self.submenu_index))
        self.submenu_type = "mode_select"
        self.submenu_index = 0
        logger.debug("Entered mode selection")

    def enter_reset_confirmation(self):
        """Enter the reset WiFi confirmation submenu."""
        self.menu_stack.append(("settings", self.submenu_index))
        self.submenu_type = "reset_confirm"
        self.submenu_index = 0
        logger.debug("Entered reset WiFi confirmation")

    def enter_display_settings(self):
        """Enter the display timeout settings editor."""
        from runtime_state import get_screen_timeout
        self.menu_stack.append(("settings", self.submenu_index))
        self.submenu_type = "display_settings"
        self.timeout_value = get_screen_timeout(default=30)
        self.original_timeout_value = self.timeout_value  # Store for cancel
        self.display_timeout_mode = "adjusting"  # Start in adjusting mode
        self.timeout_confirm_index = 0  # Reset to Save
        logger.debug(f"Entered display settings (current: {self.timeout_value}s)")

    def enter_debug_menu(self):
        """Enter the debug submenu."""
        self.menu_stack.append(("settings", self.submenu_index))
        self.submenu_type = "debug"
        self.submenu_index = 0
        logger.debug("Entered debug menu")

    def exit_submenu(self):
        """Exit current submenu, return to previous level or main screens."""
        if self.menu_stack:
            # Return to previous menu level
            prev_type, prev_index = self.menu_stack.pop()
            self.submenu_type = prev_type
            self.submenu_index = prev_index
            logger.debug(f"Returned to {prev_type} menu")
        else:
            # Exit to main screens
            self.in_submenu = False
            self.submenu_type = None
            self.submenu_index = 0
            self.needs_redraw = True  # Force immediate redraw
            logger.debug("Exited to main screens")
    
    def adjust_timeout_up(self):
        """Increase timeout value with variable step sizes."""
        if self.submenu_type != "display_settings":
            return
        
        if self.timeout_value == 0:
            # From "Never", go back to 600s
            self.timeout_value = 600
        elif self.timeout_value < 60:
            # 10-60s: increment by 10
            self.timeout_value = min(60, self.timeout_value + 10)
        elif self.timeout_value < 180:
            # 61-180s: increment by 20
            self.timeout_value = min(180, self.timeout_value + 20)
        elif self.timeout_value < 600:
            # 181-600s: increment by 30
            self.timeout_value = min(600, self.timeout_value + 30)
        else:
            # At 600s, go to "Never" (0)
            self.timeout_value = 0
    
    def adjust_timeout_down(self):
        """Decrease timeout value with variable step sizes."""
        if self.submenu_type != "display_settings":
            return
        
        if self.timeout_value == 0:
            # From "Never", go to 600s
            self.timeout_value = 600
        elif self.timeout_value <= 60:
            # 10-60s: decrement by 10
            self.timeout_value = max(10, self.timeout_value - 10)
        elif self.timeout_value <= 180:
            # 61-180s: decrement by 20
            self.timeout_value = max(60, self.timeout_value - 20)
        else:
            # 181-600s: decrement by 30
            self.timeout_value = max(180, self.timeout_value - 30)
    
    def next_menu_item(self):
        """Move to next item in current submenu with scrolling support."""
        if self.submenu_type == "settings":
            max_items = 5  # Reset WiFi, Select Mode, Display, Debug, Back
            visible_items = 4  # Show 4 items at once
            
            # Move selection
            self.submenu_index = (self.submenu_index + 1) % max_items
            
            # Update scroll offset if needed
            if self.submenu_index >= self.scroll_offset + visible_items:
                self.scroll_offset = min(self.submenu_index - visible_items + 1, max_items - visible_items)
            elif self.submenu_index < self.scroll_offset:
                self.scroll_offset = self.submenu_index
                
        elif self.submenu_type == "mode_select":
            max_items = 3  # Station, Mobile, Back
            self.submenu_index = (self.submenu_index + 1) % max_items
        elif self.submenu_type == "reset_confirm":
            max_items = 3  # Yes, No, Back
            self.submenu_index = (self.submenu_index + 1) % max_items
        elif self.submenu_type == "debug":
            max_items = 2  # Exit Program, Back
            self.submenu_index = (self.submenu_index + 1) % max_items
    
    def prev_menu_item(self):
        """Move to previous item in current submenu with scrolling support."""
        if self.submenu_type == "settings":
            max_items = 5  # Reset WiFi, Select Mode, Display, Debug, Back
            visible_items = 4  # Show 4 items at once
            
            # Move selection
            self.submenu_index = (self.submenu_index - 1) % max_items
            
            # Update scroll offset if needed
            if self.submenu_index < self.scroll_offset:
                self.scroll_offset = self.submenu_index
            elif self.submenu_index >= self.scroll_offset + visible_items:
                self.scroll_offset = min(self.submenu_index - visible_items + 1, max_items - visible_items)
                
        elif self.submenu_type == "mode_select":
            max_items = 3  # Station, Mobile, Back
            self.submenu_index = (self.submenu_index - 1) % max_items
        elif self.submenu_type == "reset_confirm":
            max_items = 3  # Yes, No, Back
            self.submenu_index = (self.submenu_index - 1) % max_items
        elif self.submenu_type == "debug":
            max_items = 2  # Exit Program, Back
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
                    # Display selected
                    self.enter_display_settings()
                    return None
                elif self.submenu_index == 3:
                    # Debug selected
                    self.enter_debug_menu()
                    return None
                elif self.submenu_index == 4:
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
            
            elif self.submenu_type == "display_settings":
                # Display settings: Two-step confirmation
                if self.display_timeout_mode == "adjusting":
                    # First button press: enter confirmation mode
                    self.display_timeout_mode = "confirming"
                    self.timeout_confirm_index = 0  # Default to Save
                    logger.debug("Entering timeout confirmation mode")
                    return None
                else:
                    # In confirming mode: handle Save/Cancel
                    if self.timeout_confirm_index == 0:
                        # Save selected
                        from runtime_state import set_screen_timeout
                        if set_screen_timeout(self.timeout_value):
                            logger.info(f"Screen timeout saved: {self.timeout_value}s")
                            self.exit_submenu()  # Return to settings menu
                            return {"type": "timeout_saved", "value": self.timeout_value}
                        else:
                            logger.error("Failed to save timeout")
                            self.display_timeout_mode = "adjusting"
                            return None
                    else:
                        # Cancel selected - restore original value
                        self.timeout_value = self.original_timeout_value
                        logger.info("Timeout change cancelled")
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
