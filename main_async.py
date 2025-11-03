# main_async.py — Async Weather Display UI with Sensor Caching
# Refactored version with async tasks and sensor/display decoupling
# Components: APC1, SHTC3, Battery, SSD1306 OLED, Rotary Encoder

import json, time, sys, machine

try:
    import uasyncio as asyncio
except ImportError:
    import asyncio

try:
    import micropython
except ImportError:
    micropython = None

from machine import I2C, Pin, WDT
from ssd1306 import SSD1306_I2C
from rotary_irq_rp2 import RotaryIRQ
from apc1 import APC1
from shtc3 import SHTC3
from battery import Battery
from config import (
    load_settings,
    FONT_SCALES,
    SETTINGS_FILE,
    get_apc1_pins,
    get_sleep_times,
    get_sensor_intervals,
    get_display_settings,
    get_ntp_settings,
)
from apc1_power import APC1Power
from display_utils import show_big
from sensor_cache import SensorCache
from screen_manager import ScreenManager
from async_tasks import (
    read_shtc3_task,
    read_apc1_task,
    read_battery_task,
    watchdog_task,
)

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
    time.sleep(0.1)

if held:
    print("DEBUG: Exited main_async.py early.")
    i2c = I2C(0, sda=Pin(16), scl=Pin(17))
    oled = SSD1306_I2C(128, 64, i2c, addr=0x3C)
    oled.fill(0)
    oled.text("DEBUG:", 0, 0)
    oled.text("Exited main", 0, 12)
    oled.show()
    for _ in range(6):
        led.toggle()
        time.sleep(0.2)
    sys.exit()

# -------- INITIALIZATION --------
print("=== Async Weather Station Starting ===")

try:
    settings = load_settings()
    sda = settings["i2c"].get("sda", 16)
    scl = settings["i2c"].get("scl", 17)
    i2c = I2C(0, sda=Pin(sda), scl=Pin(scl), freq=400000)

    # Get configuration
    DISPLAY_SLEEP_S, APC1_SLEEP_S = get_sleep_times(settings)
    SHTC3_INTERVAL, APC1_INTERVAL, BATTERY_INTERVAL = get_sensor_intervals(settings)
    DISPLAY_FPS, INPUT_POLL_HZ = get_display_settings(settings)

    print(f"Config: Display sleep={DISPLAY_SLEEP_S}s, APC1 sleep={APC1_SLEEP_S}s")
    print(f"Sensors: SHTC3={SHTC3_INTERVAL}s, APC1={APC1_INTERVAL}s, Battery={BATTERY_INTERVAL}s")
    print(f"Display: {DISPLAY_FPS} FPS, Input: {INPUT_POLL_HZ} Hz")

    oled = SSD1306_I2C(128, 64, i2c, addr=0x3C)
    devices = i2c.scan()
    print("I2C scan:", [hex(d) for d in devices])

    apc1_addr = settings.get("apc1", {}).get("address", 18)
    has_apc1 = apc1_addr in devices
    has_shtc3 = 0x70 in devices

    apc1 = APC1(i2c, apc1_addr) if has_apc1 else None
    sht = SHTC3(i2c) if has_shtc3 else None
    batt = Battery(adc_pin=26, divider_ratio=2.0)

    # Initialize watchdog timer for system stability
    wdt = WDT(timeout=8000)  # 8 second timeout (max for Pico WDT)

    # Initialize sensor cache
    cache = SensorCache()
    print("Sensor cache initialized")

    # Initialize screen manager
    screen_mgr = ScreenManager(cache, FONT_SCALES)
    print(f"Screen manager initialized: {len(screen_mgr.screens)} screens")
    
    # Initialize NTP sync if enabled
    ntp_sync = None
    ntp_cfg = get_ntp_settings(settings)
    if ntp_cfg["enabled"]:
        from ntp_helper import NTPSync
        ntp_sync = NTPSync(
            servers=ntp_cfg["servers"],
            timezone_offset_hours=ntp_cfg["timezone_offset_hours"],
            sync_interval_s=ntp_cfg["sync_interval_s"]
        )
        print(f"NTP sync configured (timezone: UTC{ntp_sync._format_offset()})")

except Exception as e:
    # Critical initialization error - show on OLED if possible
    try:
        if 'oled' in locals():
            oled.fill(0)
            oled.text("INIT ERROR", 0, 0)
            oled.text(str(e)[:20], 0, 16)
            oled.show()
        print("Initialization error:", e)
    except:
        pass
    # Reset on critical error
    machine.reset()

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

# -------- POWER MANAGEMENT --------
last_activity = time.time()
display_on = True
apc1_awake = True


def get_idle_time():
    """Get current idle time in seconds."""
    return time.time() - last_activity


def wake_up():
    """Wake up display and sensors on user activity."""
    global display_on, apc1_awake, last_activity
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
        display_on = True
        changed = True

    if changed:
        print("Wake-up triggered")


# -------- ASYNC TASKS --------

async def display_task():
    """Async task to update display from cached sensor data."""
    print(f"Display task started ({DISPLAY_FPS} FPS)")
    interval_ms = int(1000 / DISPLAY_FPS)
    
    # Initial draw
    screen_mgr.draw_screen(cache, oled)
    
    while True:
        try:
            screen_name = screen_mgr.get_current_screen_name()
            
            # Handle scrolling screen separately (needs continuous updates)
            if screen_name == "scroll":
                screen_mgr.step_scroll(cache, oled)
                oled.show()
            else:
                # Regular screen refresh based on interval
                if screen_mgr.should_refresh():
                    screen_mgr.draw_screen(cache, oled)
                    screen_mgr.mark_refreshed()
        except Exception as e:
            print(f"Display error: {e}")
        
        await asyncio.sleep_ms(interval_ms)


async def input_task():
    """Async task to handle encoder and button input."""
    print(f"Input task started ({INPUT_POLL_HZ} Hz)")
    interval_ms = int(1000 / INPUT_POLL_HZ)
    last_encoder_val = rot.value()
    
    while True:
        try:
            # Check encoder
            current_val = rot.value()
            if current_val != last_encoder_val:
                wake_up()
                
                if current_val > last_encoder_val:
                    screen_mgr.next_screen()
                else:
                    screen_mgr.prev_screen()
                
                # Draw screen immediately
                screen_mgr.draw_screen(cache, oled)
                last_encoder_val = current_val
            
            # Check button
            if not btn.value():  # Active low
                wake_up()
                action = screen_mgr.handle_button()
                
                if action == "resetwifi":
                    s = load_settings()
                    s["wifi"] = {"ssid": "", "password": ""}
                    with open(SETTINGS_FILE, "w") as f:
                        json.dump(s, f)
                    show_big(oled, ["Wi-Fi reset!", "Reboot to setup"], [1.5, 1])
                    await asyncio.sleep(2)
                
                # Debounce delay
                await asyncio.sleep_ms(200)
        
        except Exception as e:
            print(f"Input error: {e}")
        
        await asyncio.sleep_ms(interval_ms)


async def power_mgmt_task():
    """Async task to manage power states based on inactivity."""
    global display_on, apc1_awake
    
    print(f"Power mgmt started (display: {DISPLAY_SLEEP_S}s, apc1: {APC1_SLEEP_S}s)")
    
    while True:
        try:
            idle_time = get_idle_time()
            
            # Display power management
            if display_on and idle_time > DISPLAY_SLEEP_S:
                oled.poweroff()
                display_on = False
                print("Display off")
            
            # APC1 power management
            if apc1_awake and idle_time > APC1_SLEEP_S:
                apc1_power.disable()
                apc1_awake = False
                print("APC1 sleep")
        
        except Exception as e:
            print(f"Power mgmt error: {e}")
        
        # Check power state every 5 seconds
        await asyncio.sleep(5)


async def screen_update_task():
    """Periodically update available screens as sensors come online."""
    print("Screen update task started")
    
    while True:
        try:
            screen_mgr.update_available_screens()
        except Exception as e:
            print(f"Screen update error: {e}")
        
        # Check every 30 seconds
        await asyncio.sleep(30)


# -------- MAIN ASYNC LOOP --------

async def main():
    """Main async coordinator - starts all tasks."""
    print("Starting async tasks...")
    
    # Perform initial NTP sync before starting other tasks (if enabled)
    if ntp_sync:
        print("Performing initial NTP sync...")
        await ntp_sync.sync_time_async()
    
    # Create task list
    tasks = [
        asyncio.create_task(read_shtc3_task(cache, sht, SHTC3_INTERVAL)),
        asyncio.create_task(read_apc1_task(cache, apc1, APC1_INTERVAL)),
        asyncio.create_task(read_battery_task(cache, batt, BATTERY_INTERVAL)),
        asyncio.create_task(display_task()),
        asyncio.create_task(input_task()),
        asyncio.create_task(power_mgmt_task()),
        asyncio.create_task(watchdog_task(wdt, 5)),
        asyncio.create_task(screen_update_task()),
    ]
    
    # Add NTP periodic sync task if enabled
    if ntp_sync:
        from ntp_helper import ntp_sync_task
        tasks.append(asyncio.create_task(ntp_sync_task(ntp_sync, initial_sync=False)))
    
    print(f"Started {len(tasks)} async tasks")
    print("=== System Running ===")
    
    # Wait for all tasks (they run forever)
    await asyncio.gather(*tasks)


# -------- ENTRY POINT --------

try:
    asyncio.run(main())
except KeyboardInterrupt:
    oled.fill(0)
    oled.text("Stopped", 0, 20)
    oled.show()
    print("Stopped by user")
except Exception as e:
    oled.fill(0)
    oled.text("ERROR", 0, 0)
    oled.text(str(e)[:20], 0, 16)
    oled.show()
    print(f"Fatal error: {e}")
    time.sleep(5)
    machine.reset()
