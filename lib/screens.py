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
        d = apc1.read_all()
        draw_text(oled, "Particulates", 0, 0, font="PTSans_08", align="left")
        lines = [
            f"1.0:{d['PM1.0']['value']:.0f}",
            f"2.5:{d['PM2.5']['value']:.0f}",
            f"10:{d['PM10']['value']:.0f}",
        ]
        draw_block(oled, lines, 0, 16, font="helvB12", line_spacing=2)

    elif name == "aqi" and apc1:
        d = apc1.read_all()
        pm25 = d["PM2.5"]["value"]
        aqi_val = APC1.compute_aqi_pm25(pm25)
        aqi = int(aqi_val) if aqi_val is not None else 0
        draw_text(oled, "AQI", 0, 0, font="PTSans_08", align="left")
        # Use extra large font for AQI number
        draw_text(oled, f"{aqi}", 0, 20, font="PTSans_20")
        draw_text(oled, "Major:PM2.5", 0, 52, font="PTSans_06", align="left")

    elif name == "battery" and batt:
        v = batt.read_voltage()
        p = batt.read_percentage()
        draw_text(oled, "Battery", 0, 0, font="PTSans_08", align="left")
        draw_text(oled, f"{v:.2f}V", 0, 18, font="helvB12")
        draw_text(oled, f"{p:.0f}%", 80, 18, font="helvB12")

    elif name == "resetwifi":
        draw_block(oled, ["Reset Wi-Fi", "Press button"], 0, 0, font="PTSans_08", line_spacing=4)

    oled.show()
