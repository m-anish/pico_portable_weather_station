"""screens.py
Screen registry and rendering helpers

Uses display_utils draw_text/draw_block to support better fonts when available.
Falls back gracefully to built-in font.
"""

from display_utils import draw_text, draw_block
from apc1 import APC1


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
    screens += [("battery", "Battery"), ("resetwifi", "Reset Wi-Fi")]
    return screens


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
            # Use amstrad for label (PTSans_08 removed to save memory)
            draw_text(oled, "Major:PM2.5", 0, 52,
                      font="amstrad", align="left")
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

    elif name == "resetwifi":
        # Use amstrad font for title consistency
        draw_block(oled, ["Reset Wi-Fi", "Press button"],
                   0, 0, font="amstrad", line_spacing=4)

    oled.show()
