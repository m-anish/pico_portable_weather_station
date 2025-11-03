import machine, json, os, time, sys
from machine import Pin, I2C
from ssd1306 import SSD1306_I2C
import wifi_helper
from config import load_settings
from wifi_config import load_wifi_config, update_wifi

# --- Initialize OLED early ---
settings = load_settings()
sda = settings["i2c"].get("sda", 16)
scl = settings["i2c"].get("scl", 17)
i2c = I2C(0, sda=Pin(sda), scl=Pin(scl), freq=400000)
oled = SSD1306_I2C(128, 64, i2c, addr=0x3C)

# --- Failsafe: encoder button debug exit ---
ENC_SW = 20  # Encoder button pin
btn = Pin(ENC_SW, Pin.IN, Pin.PULL_UP)
led = Pin("LED", Pin.OUT)

# Hold-detect logic (1 second continuous press)
held = True
for _ in range(10):  # check for ~1.0s (10×100ms)
    if btn.value() == 1:
        held = False
        break
    time.sleep(0.1)

if held:
    print("DEBUG: Exited program.")
    oled.fill(0)
    oled.text("DEBUG:", 0, 0)
    oled.text("Exited program.", 0, 12)
    oled.show()
    for _ in range(6):
        led.toggle()
        time.sleep(0.2)
    raise KeyboardInterrupt

oled.fill(0)
oled.text("Booting...", 0, 0)
oled.show()
time.sleep(0.5)

# Load WiFi config from wifi.json ONLY
wifi_cfg = load_wifi_config()
ssid = wifi_cfg.get("ssid", "")
password = wifi_cfg.get("password", "")

# Start AP mode if no WiFi credentials configured
if not ssid:
    oled.fill(0)
    oled.text("No Wi-Fi set", 0, 0)
    oled.text("AP mode starting", 0, 12)
    oled.show()

    # Use wifi_config.update_wifi to save credentials
    def save_wifi_callback(ssid, password):
        update_wifi(ssid, password)
        print("WiFi credentials saved to wifi.json")

    wifi_helper.start_config_ap(
        ap_ssid="PICO_SETUP",
        ap_password="12345678",
        on_save=save_wifi_callback,
        oled=oled
    )
    machine.reset()

# WiFi credentials exist - let main.py handle connection
oled.fill(0)
oled.text("Wi-Fi config OK", 0, 0)
oled.text(ssid, 0, 12)
oled.text("(will connect", 0, 24)
oled.text("in main.py)", 0, 36)
oled.show()

time.sleep(0.5)
oled.fill(0)
oled.text("Starting main...", 0, 24)
oled.show()
print("Boot complete → launching main.py")

try:
    import main
except Exception as e:
    print("Error running main.py:", e)
    oled.fill(0)
    oled.text("main.py error:", 0, 0)
    oled.text(str(e)[:16], 0, 16)
    oled.show()
