# main.py — Starstuck Weather Display UI (v5)
# Components: APC1, SHTC3, Battery, SSD1306 OLED, Rotary Encoder
# Includes: Failsafe debug-exit (hold button 1s), Power Mgmt, Wake Logic

import json, time, sys, machine
from machine import I2C, Pin
from ssd1306 import SSD1306_I2C
from rotary_irq_rp2 import RotaryIRQ
from apc1 import APC1
from shtc3 import SHTC3
from battery import Battery
from config import (
    load_settings,
    FONT_SCALES,
    REFRESH_INTERVALS,
    DISPLAY_SLEEP_S,
    APC1_SLEEP_S,
    SYSTEM_SLEEP_S,
    SETTINGS_FILE,
    get_apc1_pins,
)
from screens import available_screens, draw_screen as draw_named_screen
from apc1_power import APC1Power

# --- DEBUG Failsafe check (encoder button at startup) ---
ENC_SW = 20  # encoder button pin
btn = Pin(ENC_SW, Pin.IN, Pin.PULL_UP)
led = Pin("LED", Pin.OUT)

# 1 second hold detection
held = True
for _ in range(10):  # 10×100ms = 1s
    if btn.value() == 1:
        held = False
        break
    while True:
        led.toggle()
        time.sleep(0.5)

if held:
    print("DEBUG: Exited main.py early.")
    i2c = I2C(0, sda=Pin(16), scl=Pin(17))
    oled = SSD1306_I2C(128, 64, i2c, addr=0x3C)
    oled.fill(0)
    oled.text("DEBUG:", 0, 0)
    oled.text("Exited main.py", 0, 12)
    oled.show()
    for _ in range(6):
        led.toggle()
        time.sleep(0.2)
    sys.exit()

# configuration moved to lib/config.py


# load_settings moved to lib/config.py


# text scaling and drawing helpers moved to lib/display_utils.py


# -------- INITIALIZATION --------
settings = load_settings()
sda = settings["i2c"].get("sda", 16)
scl = settings["i2c"].get("scl", 17)
i2c = I2C(0, sda=Pin(sda), scl=Pin(scl), freq=400000)

oled = SSD1306_I2C(128, 64, i2c, addr=0x3C)
devices = i2c.scan()
print("I2C scan:", devices)

apc1_addr = settings.get("apc1", {}).get("address", 18)
has_apc1 = apc1_addr in devices
has_shtc3 = 0x70 in devices

apc1 = APC1(i2c, apc1_addr) if has_apc1 else None
sht = SHTC3(i2c) if has_shtc3 else None
batt = Battery(adc_pin=26, divider_ratio=2.0)

# APC1 power helper: pins read from config with README defaults
APC1_SET_PIN, APC1_RESET_PIN = get_apc1_pins(settings)
apc1_power = APC1Power(set_pin=APC1_SET_PIN, reset_pin=APC1_RESET_PIN)

# Reset the APC1 at boot, then enable it
apc1_power.reset_pulse()
apc1_power.enable()

# Rotary encoder setup
ENC_A, ENC_B = 18, 19
rot = RotaryIRQ(pin_num_clk=ENC_A, pin_num_dt=ENC_B,
                reverse=True, range_mode=RotaryIRQ.RANGE_UNBOUNDED)
rot.set(0)


# AQI computation now provided by APC1.compute_aqi_pm25


# -------- SCREEN DEFINITIONS --------
screens = available_screens(sht, apc1)
screen_idx, last_val = 0, 0


# -------- SCREEN DRAW --------
def draw_screen():
    name = screens[screen_idx][0]
    draw_named_screen(name, oled, sht, apc1, batt, FONT_SCALES)


# -------- POWER MANAGEMENT --------
last_activity = time.time()
last_refresh = 0
display_on = True
apc1_awake = True
system_awake = True

def wake_up(_=None):
    global display_on, apc1_awake, system_awake, last_activity
    last_activity = time.time()
    changed = False

    # Wake APC1 only if it was asleep
    if apc1_awake is False or not apc1_power.is_enabled():
        apc1_power.enable()
        apc1_awake = True
        changed = True

    # Wake display only if it was off
    if not display_on:
        oled.poweron()
        draw_screen()
        display_on = True
        changed = True

    # Wake system only if it was in lightsleep
    if not system_awake:
        system_awake = True
        changed = True

    if changed:
        print("Wake-up triggered")

btn.irq(trigger=Pin.IRQ_FALLING, handler=wake_up)


# -------- MAIN LOOP --------
draw_screen()

try:
    while True:
        now = time.time()
        val = rot.value()
        if val != last_val:
            last_activity = now
            wake_up()
            if val > last_val:
                screen_idx = (screen_idx + 1) % len(screens)
            else:
                screen_idx = (screen_idx - 1) % len(screens)
            draw_screen()
            last_val = val

        if not btn.value():
            last_activity = now
            wake_up()
            if screens[screen_idx][0] == "resetwifi":
                s = load_settings()
                s["wifi"] = {"ssid": "", "password": ""}
                with open(SETTINGS_FILE, "w") as f:
                    json.dump(s, f)
                show_big(oled, ["Wi-Fi reset!", "Reboot to setup"], [1.5, 1])
                time.sleep(2)

        screen_name = screens[screen_idx][0]
        interval = REFRESH_INTERVALS.get(screen_name, 0)
        if interval > 0 and now - last_refresh > interval:
            draw_screen()
            last_refresh = now

        idle_time = now - last_activity
        if display_on and idle_time > DISPLAY_SLEEP_S:
            oled.poweroff()
            display_on = False
            print("Display off")

        if apc1_awake and idle_time > APC1_SLEEP_S:
            apc1_power.disable()
            apc1_awake = False
            print("APC1 sleep")

        if system_awake and idle_time > SYSTEM_SLEEP_S:
            print("Entering lightsleep...")
            oled.poweroff()
            apc1_power.disable()
            display_on = False
            apc1_awake = False
            system_awake = False
            machine.lightsleep()
            print("Woke from sleep")
            wake_up()

        time.sleep(0.05)

except KeyboardInterrupt:
    oled.fill(0)    
    oled.text("Stopped", 0, 20)
    oled.show()
