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
_scroll_readings = []
_scroll_index = 0
_scroll_last_update = 0
_scroll_refresh_interval = 10  # Refresh readings every 10 seconds


def available_screens(sht, apc1):
    screens = []
    if sht:
        screens.append(("sht", "Temp & Humidity"))
    if apc1:
        screens += [("pm", "Particles"), ("aqi", "AQI")]
    screens += [("battery", "Battery"), ("scroll", "Scrolling"),
                ("resetwifi", "Reset Wi-Fi")]
    return screens


def _collect_readings(sht, apc1, batt):
    """Collect all available sensor readings into formatted strings."""
    readings = []

    # Temperature and Humidity
    if sht:
        try:
            t, h = sht.measure()
            readings.append(f"Temp: {t:.1f}°C")
            readings.append(f"Humidity: {h:.1f}%")
        except Exception:
            readings.append("Temp: --")
            readings.append("Humidity: --")

    # Air quality particles
    if apc1:
        try:
            d = apc1.read_all()
            pm25 = d.get('PM2.5', {}).get('value')
            pm10 = d.get('PM10', {}).get('value')
            if pm25 is not None:
                readings.append(f"PM2.5: {pm25:.0f} µg/m³")
            if pm10 is not None:
                readings.append(f"PM10: {pm10:.0f} µg/m³")

            # AQI
            if pm25 is not None:
                aqi_val = APC1.compute_aqi_pm25(pm25)
                if aqi_val is not None:
                    readings.append(f"AQI: {int(aqi_val)}")
        except Exception:
            pass

    # Battery
    if batt:
        try:
            v = batt.read_voltage()
            p = batt.read_percentage()
            readings.append(f"Battery: {v:.2f}V ({p:.0f}%)")
        except Exception:
            readings.append("Battery: --")

    return readings if readings else ["No sensors"]


def draw_screen(name, oled, sht, apc1, batt, font_scales):
    """Render a named screen to the OLED using connected sensors."""
    global _scroll_marquee, _scroll_readings, _scroll_index
    oled.fill(0)

    if name == "sht" and sht:
        t, h = sht.measure()
        # Heading - use amstrad font for consistency
        draw_text(oled, "Temp & Humidity", 0, 0, font="amstrad", align="left")
        # Values - use large font for readability
        draw_block(oled, [f"T: {t:.1f}°C", f"H: {h:.1f}%"],
                   0, 16, font="helvB12", line_spacing=2)

    elif name == "pm" and apc1:
        try:
            d = apc1.read_all()
            # Title with units in parentheses
            # Use amstrad font which supports µ and ³
            draw_text(oled, "Particles (µg/m³)", 0, 0,
                      font="amstrad", align="left")
            lines = []
            # Only show PM2.5 and PM10, handle missing data gracefully
            pm25_val = (d.get('PM2.5', {}).get('value')
                        if 'PM2.5' in d else None)
            pm10_val = (d.get('PM10', {}).get('value')
                        if 'PM10' in d else None)

            # Format with space after colon, use larger font for values
            if pm25_val is not None:
                lines.append(f"PM2.5: {pm25_val:.0f}")
            else:
                lines.append("PM2.5: --")

            if pm10_val is not None:
                lines.append(f"PM10: {pm10_val:.0f}")
            else:
                lines.append("PM10: --")

            if lines:
                # Use larger font (helvB12) for better readability
                draw_block(oled, lines, 0, 16, font="helvB12", line_spacing=2)
            else:
                draw_text(oled, "No data", 0, 20, font="amstrad")
        except Exception:
            draw_text(oled, "Particles (µg/m³)", 0, 0,
                      font="amstrad", align="left")
            draw_text(oled, "Sensor Error", 0, 20, font="amstrad")

    elif name == "aqi" and apc1:
        try:
            d = apc1.read_all()
            pm25 = (d.get("PM2.5", {}).get("value")
                    if "PM2.5" in d else None)

            if pm25 is not None:
                aqi_val = APC1.compute_aqi_pm25(pm25)
                aqi = int(aqi_val) if aqi_val is not None else None
            else:
                aqi = None

            # Use amstrad font for title consistency
            draw_text(oled, "AQI", 0, 0, font="amstrad", align="left")

            if aqi is not None:
                # Use extra large font for AQI number
                draw_text(oled, f"{aqi}", 0, 20, font="PTSans_20")
                # Make "Major:PM2.5" slightly larger
                draw_text(oled, "Major:PM2.5", 0, 52,
                          font="PTSans_08", align="left")
            else:
                draw_text(oled, "--", 0, 20, font="PTSans_20")
                draw_text(oled, "No data", 0, 52, font="amstrad", align="left")
        except Exception:
            draw_text(oled, "AQI", 0, 0, font="amstrad", align="left")
            draw_text(oled, "Error", 0, 20, font="amstrad")

    elif name == "battery" and batt:
        v = batt.read_voltage()
        p = batt.read_percentage()
        # Use amstrad font for title consistency
        draw_text(oled, "Battery", 0, 0, font="amstrad", align="left")
        draw_text(oled, f"{v:.2f}V", 0, 18, font="helvB12")
        draw_text(oled, f"{p:.0f}%", 80, 18, font="helvB12")

    elif name == "scroll":
        # Scrolling screen - show title and initialize marquee if needed
        # Don't fill screen - let marquee manage its area
        # Only clear and redraw title area (top 16 pixels)
        for y in range(0, 16):
            for x in range(128):
                oled.pixel(x, y, 0)
        draw_text(oled, "All Readings", 0, 0, font="amstrad", align="left")

        # Collect all readings and initialize last update time
        global _scroll_readings, _scroll_last_update
        _scroll_readings = _collect_readings(sht, apc1, batt)
        _scroll_last_update = time.time()

        # Initialize marquee if needed - use larger font for readability
        if _scroll_marquee is None:
            _scroll_marquee = Marquee(oled, x=0, y=20, width=128,
                                      font="helvB12", speed_px=1)

        # If we have readings, start with current index
        if _scroll_readings:
            if _scroll_index >= len(_scroll_readings):
                _scroll_index = 0
            current_text = _scroll_readings[_scroll_index]
            _scroll_marquee.start(current_text)
        else:
            # Clear marquee area if no data
            for y in range(20, 64):
                for x in range(128):
                    oled.pixel(x, y, 0)
            draw_text(oled, "No data", 0, 40, font="amstrad", align="left")

    elif name == "resetwifi":
        # Use amstrad font for title consistency
        draw_block(oled, ["Reset Wi-Fi", "Press button"],
                   0, 0, font="amstrad", line_spacing=4)

    # Stop marquee when leaving scroll screen
    if name != "scroll" and _scroll_marquee:
        _scroll_marquee.stop()
        _scroll_marquee = None
        _scroll_index = 0

    oled.show()


def step_scroll_screen(oled, sht, apc1, batt, current_time):
    """Step the scrolling marquee when scroll screen is active.

    Args:
        oled: Display device
        sht: SHTC3 sensor instance (or None)
        apc1: APC1 sensor instance (or None)
        batt: Battery instance (or None)
        current_time: Current time.time() value

    Returns True if marquee completed (time to switch to next reading).
    """
    global _scroll_marquee, _scroll_index
    global _scroll_readings, _scroll_last_update

    # Ensure marquee is initialized
    if _scroll_marquee is None:
        return False

    # Refresh readings periodically
    if (current_time - _scroll_last_update) >= _scroll_refresh_interval:
        new_readings = _collect_readings(sht, apc1, batt)
        if new_readings != _scroll_readings:
            _scroll_readings = new_readings
            _scroll_last_update = current_time
            # Reset index if current reading no longer exists
            if _scroll_index >= len(_scroll_readings):
                _scroll_index = 0
            # Restart marquee with new readings if needed
            if _scroll_readings:
                current_text = _scroll_readings[_scroll_index]
                _scroll_marquee.start(current_text)

    # Only redraw title if needed (to avoid interfering with marquee)
    # The marquee step() will handle its own area

    # Ensure marquee is active with current reading
    if not _scroll_marquee.active() and _scroll_readings:
        current_text = _scroll_readings[_scroll_index]
        _scroll_marquee.start(current_text)

    # Step the marquee (this handles its own area clearing and redrawing)
    if _scroll_marquee.active():
        # Redraw title first (in case it got cleared)
        draw_text(oled, "All Readings", 0, 0, font="amstrad", align="left")
        # Step the marquee
        completed = _scroll_marquee.step()

        if completed and _scroll_readings:
            # Move to next reading when marquee completes
            _scroll_index = (_scroll_index + 1) % len(_scroll_readings)
            next_text = _scroll_readings[_scroll_index]
            _scroll_marquee.start(next_text)

        return completed

    return False
