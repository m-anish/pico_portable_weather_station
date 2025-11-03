"""screens.py
Screen registry and rendering helpers

Uses display_utils draw_text/draw_block to support better fonts when available.
Falls back gracefully to built-in font.
"""

from display_utils import draw_text, draw_block
from apc1 import APC1


def available_screens(cache):
    """Return fixed list of all screens regardless of sensor availability.
    
    Screens will display informative messages when sensor data is unavailable
    rather than being hidden from the navigation.
    
    Args:
        cache: SensorCache instance (not used, kept for compatibility)
    
    Returns:
        list: List of (screen_id, screen_name) tuples
    """
    return [
        ("sht", "Temp & Humidity"),
        ("pm", "Particles"),
        ("gases", "Gases"),
        ("aqi", "AQI"),
        ("sysinfo", "System Info"),
        ("settings", "Settings")
    ]


def draw_screen(name, oled, cache, font_scales):
    """Render a named screen to the OLED using cached sensor data.
    
    Args:
        name: Screen name/ID
        oled: SSD1306 display instance
        cache: SensorCache instance
        font_scales: Dictionary of font scales (legacy, may be unused)
    """
    oled.fill(0)

    if name == "sht":
        # Get cached SHTC3 data
        t, h, _ = cache.get_shtc3()
        
        # Heading - use amstrad font for consistency
        draw_text(oled, "Temp & Humidity", 0, 0, font="amstrad", align="left")
        
        if t is not None and h is not None:
            # Values - use large font for readability
            draw_block(oled, [f"T: {t:.1f}°C", f"H: {h:.1f}%"],
                       0, 16, font="helvB12", line_spacing=2)
        else:
            # Sensor not available - show informative message
            draw_text(oled, "SHTC3 sensor", 0, 20, font="amstrad")
            draw_text(oled, "not detected", 0, 32, font="amstrad")

    elif name == "pm":
        # Get cached PM data
        pm1, pm25, pm10, _ = cache.get_apc1_pm()
        
        # Title with units in parentheses
        # Use amstrad font which supports µ and ³
        draw_text(oled, "Particles (µg/m³)", 0, 0,
                  font="amstrad", align="left")
        
        if pm25 is not None:
            # Has data - show values
            lines = [f"PM2.5: {pm25:.0f}", f"PM10: {pm10:.0f}"]
            draw_block(oled, lines, 0, 16, font="helvB12", line_spacing=2)
        else:
            # Sensor not available - show informative message
            draw_text(oled, "APC1 sensor", 0, 20, font="amstrad")
            draw_text(oled, "not detected", 0, 32, font="amstrad")

    elif name == "gases":
        # Get cached gas concentration data
        tvoc, eco2, _ = cache.get_apc1_gases()
        
        # Title with units in parentheses
        draw_text(oled, "Gases (ppb)", 0, 0, font="amstrad", align="left")
        
        if tvoc is not None and eco2 is not None:
            # Has data - show values
            lines = [f"TVOC: {tvoc:.0f}", f"eCO2: {eco2:.0f}"]
            draw_block(oled, lines, 0, 16, font="helvB12", line_spacing=2)
        else:
            # Sensor not available - show informative message
            draw_text(oled, "APC1 sensor", 0, 20, font="amstrad")
            draw_text(oled, "not detected", 0, 32, font="amstrad")

    elif name == "aqi":
        # Get cached AQI data
        aqi_pm25, aqi_tvoc, pm25, _ = cache.get_apc1_aqi()
        
        # Use amstrad font for title consistency
        draw_text(oled, "AQI", 0, 0, font="amstrad", align="left")

        if aqi_pm25 is not None:
            # Use extra large font for AQI number
            draw_text(oled, f"{int(aqi_pm25)}", 0, 20, font="PTSans_20")
            # Use amstrad for label (PTSans_08 removed to save memory)
            draw_text(oled, "Major:PM2.5", 0, 52,
                      font="amstrad", align="left")
        else:
            # Sensor not available - show informative message
            draw_text(oled, "APC1 sensor", 0, 20, font="amstrad")
            draw_text(oled, "not detected", 0, 32, font="amstrad")

    elif name == "sysinfo":
        # Get cached battery data
        v, p, _ = cache.get_battery()
        
        # Title
        draw_text(oled, "System Info", 0, 0, font="amstrad", align="left")
        
        # Battery status
        draw_text(oled, "Battery:", 0, 12, font="amstrad", align="left")
        if v is not None:
            if v >= 4.25:
                # Charging
                draw_text(oled, "Charging", 0, 24, font="amstrad", align="left")
            else:
                # Show voltage and percentage
                draw_text(oled, f"{v:.2f}V  {p:.0f}%", 0, 24, font="amstrad", align="left")
        else:
            draw_text(oled, "--", 0, 24, font="amstrad", align="left")
        
        # IP Address
        draw_text(oled, "IP:", 0, 38, font="amstrad", align="left")
        try:
            import wifi_helper
            if wifi_helper.is_connected():
                ip = wifi_helper.get_ip_address()
                # Truncate if too long (max ~16 chars for amstrad font)
                if len(ip) > 15:
                    ip = ip[-15:]  # Show last 15 chars
                draw_text(oled, ip, 0, 50, font="amstrad", align="left")
            else:
                draw_text(oled, "Not connected", 0, 50, font="amstrad", align="left")
        except Exception as e:
            draw_text(oled, "N/A", 0, 50, font="amstrad", align="left")

    elif name == "settings":
        # Settings menu entry screen
        draw_text(oled, "SETTINGS", 0, 0, font="amstrad", align="left")
        oled.hline(0, 10, 128, 1)
        draw_text(oled, "Press to enter", 0, 20, font="amstrad")
    
    oled.show()


def draw_settings_menu(oled, selected_index=0, scroll_offset=0):
    """Draw the settings submenu with options and scrolling support.
    
    Args:
        oled: SSD1306 display instance
        selected_index: Currently selected menu item (0-based)
        scroll_offset: Scroll offset for viewing window (0-based)
    """
    options = ["Reset WiFi", "Select Mode", "Display", "Debug", "Back"]
    visible_items = 4  # Show 4 items at once
    
    oled.fill(0)
    draw_text(oled, "SETTINGS", 0, 0, font="amstrad", align="left")
    oled.hline(0, 10, 128, 1)
    
    # Show scroll indicators if needed
    if scroll_offset > 0:
        # Can scroll up - show up arrow
        draw_text(oled, "^", 120, 12, font="amstrad", align="left")
    
    if scroll_offset + visible_items < len(options):
        # Can scroll down - show down arrow
        draw_text(oled, "v", 120, 52, font="amstrad", align="left")
    
    # Draw visible menu options with selection indicator
    for i in range(visible_items):
        option_index = scroll_offset + i
        if option_index >= len(options):
            break
        
        y = 15 + i * 12
        prefix = "> " if option_index == selected_index else "  "
        draw_text(oled, prefix + options[option_index], 0, y, font="amstrad", align="left")
    
    oled.show()


def draw_mode_selection(oled, selected_index=0, current_mode="mobile"):
    """Draw the mode selection submenu.
    
    Args:
        oled: SSD1306 display instance
        selected_index: Currently selected mode (0-based)
        current_mode: Current operation mode ("station" or "mobile")
    """
    modes = [
        ("Station", "station"),
        ("Mobile", "mobile"),
        ("Back", None)
    ]
    
    oled.fill(0)
    draw_text(oled, "SELECT MODE", 0, 0, font="amstrad", align="left")
    oled.hline(0, 10, 128, 1)
    
    # Draw mode options with selection and current mode indicators
    for i, (label, mode_val) in enumerate(modes):
        y = 15 + i * 12
        prefix = "> " if i == selected_index else "  "
        suffix = " *" if mode_val and mode_val == current_mode else ""
        draw_text(oled, prefix + label + suffix, 0, y, font="amstrad", align="left")
    
    oled.show()


def draw_reset_confirmation(oled, selected_index=0):
    """Draw the Reset WiFi confirmation screen.
    
    Args:
        oled: SSD1306 display instance
        selected_index: Currently selected option (0-based)
    """
    options = ["Yes", "No", "Back"]
    
    oled.fill(0)
    draw_text(oled, "RESET WIFI?", 0, 0, font="amstrad", align="left")
    oled.hline(0, 10, 128, 1)
    draw_text(oled, "Are you sure?", 0, 14, font="amstrad", align="left")
    
    # Draw confirmation options with selection indicator
    for i, option in enumerate(options):
        y = 30 + i * 12
        prefix = "> " if i == selected_index else "  "
        draw_text(oled, prefix + option, 0, y, font="amstrad", align="left")
    
    oled.show()


def draw_display_settings(oled, timeout_value, mode="adjusting", confirm_index=0):
    """Draw the display settings screen for adjusting timeout.
    
    Args:
        oled: SSD1306 display instance
        timeout_value: Current timeout value in seconds (0 means "Never")
        mode: "adjusting" or "confirming"
        confirm_index: Selected option in confirming mode (0=Save, 1=Cancel)
    """
    oled.fill(0)
    draw_text(oled, "DISPLAY TIMEOUT", 0, 0, font="amstrad", align="left")
    oled.hline(0, 10, 128, 1)
    
    if mode == "adjusting":
        # Adjusting mode: show value and instructions
        if timeout_value == 0:
            value_text = "Never"
        else:
            value_text = f"{timeout_value}s"
        
        # Center the value - calculate x position manually for better centering
        # Approximate character width for helvB12: ~12 pixels per char
        text_width = len(value_text) * 12
        x_pos = (128 - text_width) // 2
        draw_text(oled, value_text, x_pos, 24, font="helvB12", align="left")
        
        # Instructions
        draw_text(oled, "Turn: adjust", 0, 44, font="amstrad", align="left")
        draw_text(oled, "Press: confirm", 0, 54, font="amstrad", align="left")
    
    else:
        # Confirming mode: show Save/Cancel options
        if timeout_value == 0:
            value_text = "Never"
        else:
            value_text = f"{timeout_value}s"
        
        draw_text(oled, f"Save: {value_text}", 0, 14, font="amstrad", align="left")
        oled.hline(0, 24, 128, 1)
        
        # Draw Save/Cancel options
        options = ["Save", "Cancel"]
        for i, option in enumerate(options):
            y = 28 + i * 12
            prefix = "> " if i == confirm_index else "  "
            draw_text(oled, prefix + option, 0, y, font="amstrad", align="left")
    
    oled.show()


def draw_debug_menu(oled, selected_index=0):
    """Draw the debug submenu with options.
    
    Args:
        oled: SSD1306 display instance
        selected_index: Currently selected menu item (0-based)
    """
    options = ["Exit Program", "Back"]
    
    oled.fill(0)
    draw_text(oled, "DEBUG", 0, 0, font="amstrad", align="left")
    oled.hline(0, 10, 128, 1)
    
    # Draw menu options with selection indicator
    for i, option in enumerate(options):
        y = 15 + i * 12
        prefix = "> " if i == selected_index else "  "
        draw_text(oled, prefix + option, 0, y, font="amstrad", align="left")
    
    oled.show()
