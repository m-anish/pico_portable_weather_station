"""screens.py
Screen registry and rendering helpers

Uses display_utils draw_text/draw_block to support better fonts when available.
Falls back gracefully to built-in font.
"""

from display_utils import show_big, draw_text, draw_block
from apc1 import APC1


def available_screens(sht, apc1):
    screens = []
    if sht:
        screens.append(("sht", "Temp & Humidity"))
    if apc1:
        screens += [("pm", "Particulates"), ("aqi", "AQI")]
    screens += [("battery", "Battery"), ("resetwifi", "Reset Wi-Fi")]
    return screens


def draw_screen(name, oled, sht, apc1, batt, font_scales):
    """Render a named screen to the OLED using connected sensors."""
    oled.fill(0)

    if name == "sht" and sht:
        t, h = sht.measure()
        # Heading - use medium font
        draw_text(oled, "Temp & Humidity", 0, 0, font="PTSans_08", align="left")
        # Values - use large font for readability
        draw_block(oled, [f"T: {t:.1f}°C", f"H: {h:.1f}%"], 0, 16, font="helvB12", line_spacing=2)

    elif name == "pm" and apc1:
        try:
            d = apc1.read_all()
            draw_text(oled, "Particulates", 0, 0, font="PTSans_08", align="left")
            lines = []
            # Only show PM2.5 and PM10, handle missing data gracefully
            pm25_val = d.get('PM2.5', {}).get('value') if 'PM2.5' in d else None
            pm10_val = d.get('PM10', {}).get('value') if 'PM10' in d else None
            
            # Format with space after colon and units (µg/m³)
            # Use amstrad font which supports µ (mu) and ³ (superscript 3) characters
            if pm25_val is not None:
                lines.append(f"PM2.5: {pm25_val:.0f} µg/m³")
            else:
                lines.append("PM2.5: -- µg/m³")
                
            if pm10_val is not None:
                lines.append(f"PM10: {pm10_val:.0f} µg/m³")
            else:
                lines.append("PM10: -- µg/m³")
                
            if lines:
                # Use amstrad font which definitely supports µ and ³ characters
                # This ensures proper display of µg/m³ units
                draw_block(oled, lines, 0, 16, font="amstrad", line_spacing=3)
            else:
                draw_text(oled, "No data", 0, 20, font="PTSans_08")
        except Exception as e:
            draw_text(oled, "Particulates", 0, 0, font="PTSans_08", align="left")
            draw_text(oled, "Sensor Error", 0, 20, font="PTSans_08")

    elif name == "aqi" and apc1:
        try:
            d = apc1.read_all()
            pm25 = d.get("PM2.5", {}).get("value") if "PM2.5" in d else None
            
            if pm25 is not None:
                aqi_val = APC1.compute_aqi_pm25(pm25)
                aqi = int(aqi_val) if aqi_val is not None else None
            else:
                aqi = None
                
            draw_text(oled, "AQI", 0, 0, font="PTSans_08", align="left")
            
            if aqi is not None:
                # Use extra large font for AQI number
                draw_text(oled, f"{aqi}", 0, 20, font="PTSans_20")
                # Make "Major:PM2.5" slightly larger (use PTSans_08 instead of PTSans_06)
                draw_text(oled, "Major:PM2.5", 0, 52, font="PTSans_08", align="left")
            else:
                draw_text(oled, "--", 0, 20, font="PTSans_20")
                draw_text(oled, "No data", 0, 52, font="PTSans_08", align="left")
        except Exception as e:
            draw_text(oled, "AQI", 0, 0, font="PTSans_08", align="left")
            draw_text(oled, "Error", 0, 20, font="PTSans_08")

    elif name == "battery" and batt:
        v = batt.read_voltage()
        p = batt.read_percentage()
        draw_text(oled, "Battery", 0, 0, font="PTSans_08", align="left")
        draw_text(oled, f"{v:.2f}V", 0, 18, font="helvB12")
        draw_text(oled, f"{p:.0f}%", 80, 18, font="helvB12")

    elif name == "resetwifi":
        draw_block(oled, ["Reset Wi-Fi", "Press button"], 0, 0, font="PTSans_08", line_spacing=4)

    oled.show()
