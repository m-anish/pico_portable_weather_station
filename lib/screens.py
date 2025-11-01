"""screens.py
Screen registry and rendering helpers

Uses display_utils draw_text/draw_block to support better fonts when available.
Falls back gracefully to built-in font.
"""

from display_utils import draw_text, draw_block
from apc1 import APC1


def available_screens(sht, apc1):
    screens = []
    if sht:
        screens.append(("sht", "Temp & Humidity"))
    if apc1:
        screens += [("pm", "Particles"), ("aqi", "AQI")]
    screens += [("battery", "Battery"), ("resetwifi", "Reset Wi-Fi")]
    return screens


def draw_screen(name, oled, sht, apc1, batt, font_scales):
    """Render a named screen to the OLED using connected sensors."""
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

    elif name == "resetwifi":
        # Use amstrad font for title consistency
        draw_block(oled, ["Reset Wi-Fi", "Press button"],
                   0, 0, font="amstrad", line_spacing=4)

    oled.show()
