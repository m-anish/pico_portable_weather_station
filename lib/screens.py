"""screens.py
Screen registry and rendering helpers

Uses display_utils draw_text/draw_block to support better fonts when available.
Falls back gracefully to built-in font.
"""

import time
from display_utils import draw_text, draw_block, Marquee
from apc1 import APC1

# Global state for scrolling screen
_scroll_marquee = None
_scroll_text = ""
_scroll_last_update = 0
_scroll_refresh_interval = 10  # Refresh readings every 10 seconds


def available_screens(cache):
    """Return list of available screens based on cached sensor data.
    
    Args:
        cache: SensorCache instance
    
    Returns:
        list: List of (screen_id, screen_name) tuples
    """
    screens = []
    if cache.has_shtc3_data():
        screens.append(("sht", "Temp & Humidity"))
    if cache.has_apc1_data():
        screens += [("pm", "Particles"), ("aqi", "AQI")]
    screens += [("battery", "Battery"), ("scroll", "Scrolling"),
                ("resetwifi", "Reset Wi-Fi")]
    return screens


def _collect_readings(cache):
    """Collect all available sensor readings from cache into a single formatted string for scrolling.
    
    Args:
        cache: SensorCache instance
    
    Returns:
        str: Formatted string of all sensor readings
    """
    readings = []
    
    # Get all cached data
    data = cache.get_all_for_scroll()

    # Temperature and Humidity
    t = data.get('temperature')
    h = data.get('humidity')
    if t is not None and h is not None:
        readings.append(f"Temp: {t:.1f}°C")
        readings.append(f"Humidity: {h:.1f}%")
    elif cache.has_shtc3_data():
        readings.append("Temp: --")
        readings.append("Humidity: --")

    # Air quality particles
    pm25 = data.get('pm25')
    pm10 = data.get('pm10')
    aqi_pm25 = data.get('aqi_pm25')
    
    if pm25 is not None:
        readings.append(f"PM2.5: {pm25:.0f} µg/m³")
    if pm10 is not None:
        readings.append(f"PM10: {pm10:.0f} µg/m³")
    if aqi_pm25 is not None:
        readings.append(f"AQI: {int(aqi_pm25)}")

    # Battery
    v = data.get('battery_voltage')
    p = data.get('battery_percent')
    if v is not None and p is not None:
        readings.append(f"Battery: {v:.2f}V ({p:.0f}%)")
    elif cache.has_battery_data():
        readings.append("Battery: --")

    # Join into a single string with separators for continuous scrolling
    if readings:
        return " | ".join(readings)
    else:
        return "No sensors"


def draw_screen(name, oled, cache, font_scales):
    """Render a named screen to the OLED using cached sensor data.
    
    Args:
        name: Screen name/ID
        oled: SSD1306 display instance
        cache: SensorCache instance
        font_scales: Dictionary of font scales (legacy, may be unused)
    """
    global _scroll_marquee, _scroll_text
    oled.fill(0)

    if name == "sht":
        # Get cached SHTC3 data
        t, h, _ = cache.get_shtc3()
        
        # Heading - use amstrad font for consistency
        draw_text(oled, "Temp & Humidity", 0, 0, font="amstrad", align="left")
        # Values - use large font for readability
        if t is not None and h is not None:
            draw_block(oled, [f"T: {t:.1f}°C", f"H: {h:.1f}%"],
                       0, 16, font="helvB12", line_spacing=2)
        else:
            draw_block(oled, ["T: --", "H: --"], 0, 16, font="helvB12", line_spacing=2)

    elif name == "pm":
        # Get cached PM data
        pm1, pm25, pm10, _ = cache.get_apc1_pm()
        
        # Title with units in parentheses
        # Use amstrad font which supports µ and ³
        draw_text(oled, "Particles (µg/m³)", 0, 0,
                  font="amstrad", align="left")
        lines = []
        
        # Format with space after colon, use larger font for values
        if pm25 is not None:
            lines.append(f"PM2.5: {pm25:.0f}")
        else:
            lines.append("PM2.5: --")

        if pm10 is not None:
            lines.append(f"PM10: {pm10:.0f}")
        else:
            lines.append("PM10: --")

        if lines:
            # Use larger font (helvB12) for better readability
            draw_block(oled, lines, 0, 16, font="helvB12", line_spacing=2)
        else:
            draw_text(oled, "No data", 0, 20, font="amstrad")

    elif name == "aqi":
        # Get cached AQI data
        aqi_pm25, aqi_tvoc, pm25, _ = cache.get_apc1_aqi()
        
        # Use amstrad font for title consistency
        draw_text(oled, "AQI", 0, 0, font="amstrad", align="left")

        if aqi_pm25 is not None:
            # Use extra large font for AQI number
            draw_text(oled, f"{int(aqi_pm25)}", 0, 20, font="PTSans_20")
            # Make "Major:PM2.5" slightly larger
            draw_text(oled, "Major:PM2.5", 0, 52,
                      font="PTSans_08", align="left")
        else:
            draw_text(oled, "--", 0, 20, font="PTSans_20")
            draw_text(oled, "No data", 0, 52, font="amstrad", align="left")

    elif name == "battery":
        # Get cached battery data
        v, p, _ = cache.get_battery()
        
        # Use amstrad font for title consistency
        draw_text(oled, "Battery", 0, 0, font="amstrad", align="left")
        if v is not None and p is not None:
            draw_text(oled, f"{v:.2f}V", 0, 18, font="helvB12")
            draw_text(oled, f"{p:.0f}%", 80, 18, font="helvB12")
        else:
            draw_text(oled, "--", 0, 18, font="helvB12")
            draw_text(oled, "--", 80, 18, font="helvB12")

    elif name == "scroll":
        # Scrolling screen - show title and initialize marquee if needed
        # Don't fill screen - let marquee manage its area
        # Only clear and redraw title area (top 16 pixels)
        oled.fill_rect(0, 0, 128, 16, 0)
        draw_text(oled, "All Readings", 0, 0, font="amstrad", align="left")

        # Collect all readings from cache into a string
        global _scroll_text, _scroll_last_update
        _scroll_text = _collect_readings(cache)
        _scroll_last_update = time.time()

        # Initialize marquee if needed - use larger font for readability
        if _scroll_marquee is None:
            _scroll_marquee = Marquee(oled, x=0, y=20, width=128,
                                      font="helvB12", speed_px=1)

        # Start marquee with the full text
        if _scroll_text:
            _scroll_marquee.start(_scroll_text)
        else:
            # Clear marquee area if no data
            oled.fill_rect(0, 20, 128, 44, 0)
            draw_text(oled, "No data", 0, 40, font="amstrad", align="left")

    elif name == "resetwifi":
        # Use amstrad font for title consistency
        draw_block(oled, ["Reset Wi-Fi", "Press button"],
                   0, 0, font="amstrad", line_spacing=4)

    # Stop marquee when leaving scroll screen
    if name != "scroll" and _scroll_marquee:
        _scroll_marquee.stop()
        _scroll_marquee = None

    oled.show()


def step_scroll_screen(oled, cache, current_time):
    """Step the scrolling marquee when scroll screen is active.

    Args:
        oled: Display device
        cache: SensorCache instance
        current_time: Current time.time() value

    Returns True (always, since it's continuous scrolling).
    """
    global _scroll_marquee, _scroll_text

    # Ensure marquee is initialized
    if _scroll_marquee is None:
        return False

    # Ensure marquee is active
    if not _scroll_marquee.active() and _scroll_text:
        _scroll_marquee.start(_scroll_text)

    # Step the marquee (continuous scrolling)
    if _scroll_marquee.active():
        # Redraw title first (in case it got cleared)
        draw_text(oled, "All Readings", 0, 0, font="amstrad", align="left")
        # Step the marquee
        completed = _scroll_marquee.step()

        # Refresh readings only after a full scroll cycle completes
        if completed:
            new_text = _collect_readings(cache)
            if new_text != _scroll_text:
                _scroll_text = new_text
                # Restart marquee with updated text
                if _scroll_text:
                    _scroll_marquee.start(_scroll_text)

    return True
