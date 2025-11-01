import machine, json, os, time, sys
from machine import Pin, I2C
from ssd1306 import SSD1306_I2C
import wifi_helper

SETTINGS_FILE = "settings.json"

def load_settings():
    if SETTINGS_FILE in os.listdir():
        try:
            with open(SETTINGS_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return {"wifi": {"ssid": "", "password": ""},
            "i2c": {"sda": 16, "scl": 17}}

def save_wifi_settings(ssid, password):
    s = load_settings()
    s["wifi"] = {"ssid": ssid, "password": password}
    with open(SETTINGS_FILE, "w") as f:
        json.dump(s, f)
    print("Saved new Wi-Fi credentials")

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
    print("DEBUG mode active. Halted execution.")
    while True:
        led.toggle()
        time.sleep(0.5)

if held:
    oled.fill(0)
    oled.text("DEBUG:", 0, 0)
    oled.text("Exited program.", 0, 12)
    oled.show()
    print("DEBUG: Exited program.")
    for _ in range(6):
        led.toggle()
        time.sleep(0.2)
    sys.exit()

oled.fill(0)
oled.text("Booting...", 0, 0)
oled.show()
time.sleep(0.5)

wifi = settings.get("wifi", {})
ssid = wifi.get("ssid", "")
password = wifi.get("password", "")

connected = False

if ssid and password:
    oled.fill(0)
    oled.text("Wi-Fi:", 0, 0)
    oled.text(ssid, 0, 12)
    oled.text("Connecting...", 0, 24)
    oled.show()

    connected = wifi_helper.connect(ssid, password, oled=oled)
    if connected:
        oled.text("OK", 0, 48)
        oled.show()
    else:
        oled.fill(0)
        oled.text("Wi-Fi failed!", 0, 0)
        oled.text("Continuing...", 0, 16)
        oled.show()
        print("Wi-Fi connection failed; continuing without network.")
        time.sleep(1)
else:
    oled.fill(0)
    oled.text("No Wi-Fi set", 0, 0)
    oled.text("AP mode starting", 0, 12)
    oled.show()

    wifi_helper.start_config_ap(
        ap_ssid="PICO_SETUP",
        ap_password="12345678",
        on_save=save_wifi_settings,
        oled=oled
    )
    machine.reset()

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
