# screens.py
# Screen registry and rendering helpers

from display_utils import show_big
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
        show_big(oled, [f"T: {t:.1f}°C", f"H: {h:.1f}%"], font_scales["temp_hum"])

    elif name == "pm" and apc1:
        d = apc1.read_all()
        show_big(
            oled,
            [
                "Particulates",
                f"1.0:{d['PM1.0']['value']:.0f}",
                f"2.5:{d['PM2.5']['value']:.0f}",
                f"10:{d['PM10']['value']:.0f}",
            ],
            font_scales["pm"],
        )

    elif name == "aqi" and apc1:
        d = apc1.read_all()
        pm25 = d["PM2.5"]["value"]
        aqi_val = APC1.compute_aqi_pm25(pm25)
        aqi = int(aqi_val) if aqi_val is not None else 0
        show_big(oled, [f"AQI:{aqi}", "Major:PM2.5"], font_scales["aqi"])

    elif name == "battery" and batt:
        v = batt.read_voltage()
        p = batt.read_percentage()
        show_big(oled, [f"{v:.2f}V", f"{p:.0f}%"], font_scales["battery"])

    elif name == "resetwifi":
        show_big(oled, ["Reset Wi-Fi", "Press button"], font_scales["resetwifi"])

    oled.show()
