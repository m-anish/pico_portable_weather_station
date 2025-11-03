# main_async.py — Async Weather Display UI with Sensor Caching
# Refactored version with async tasks and sensor/display decoupling
# Components: APC1, SHTC3, Battery, SSD1306 OLED, Rotary Encoder

import json, time, sys, machine, gc

try:
    import uasyncio as asyncio
except ImportError:
    import asyncio

try:
    import micropython
except ImportError:
    micropython = None


def log_memory(label):
    """Helper to log memory status with label."""
    free = gc.mem_free() / 1024
    used = gc.mem_alloc() / 1024
    print(f"[{label}] MEM: {free:.1f}KB free, {used:.1f}KB used")

from machine import I2C, Pin
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
    get_screen_timeout,
    get_sensor_intervals,
    get_display_settings,
    get_ntp_settings,
    get_blynk_settings,
    get_wifi_settings,
    get_operation_mode,
    get_station_mode_settings,
    get_webserver_settings,  # <-- ADDED WEBSERVER IMPORT
)
import wifi_helper
from apc1_power import APC1Power
from display_utils import show_big
from sensor_cache import SensorCache
from screen_manager import ScreenManager
from async_tasks import (
    read_shtc3_task,
    read_apc1_task,
    read_battery_task,
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
    raise KeyboardInterrupt

# -------- INITIALIZATION --------
print("=== Async Weather Station Starting ===")

try:
    settings = load_settings()
    sda = settings["i2c"].get("sda", 16)
    scl = settings["i2c"].get("scl", 17)
    # Use 400kHz - works with OLED and APC1 (despite datasheet stating 100kHz)
    i2c = I2C(0, sda=Pin(sda), scl=Pin(scl), freq=400000)

    # Get configuration
    SHTC3_INTERVAL, APC1_INTERVAL, BATTERY_INTERVAL = get_sensor_intervals(settings)
    DISPLAY_FPS, INPUT_POLL_HZ = get_display_settings(settings)

    print(f"Sensors: SHTC3={SHTC3_INTERVAL}s, APC1={APC1_INTERVAL}s, Battery={BATTERY_INTERVAL}s")
    print(f"Display: {DISPLAY_FPS} FPS, Input: {INPUT_POLL_HZ} Hz")

    oled = SSD1306_I2C(128, 64, i2c, addr=0x3C)

    # Display splash screen
    oled.fill(0)
    # Center text on 128x64 display
    # "starstucklab.com" = 16 chars * 8px = 128px (fits perfectly)
    # "PicoWeather" = 11 chars * 8px = 88px, center at (128-88)/2 = 20
    oled.text("starstucklab.com", 0, 20)
    oled.text("PicoWeather", 20, 32)
    oled.show()
    time.sleep(2)  # Show splash for 2 seconds

    # Initialize APC1 power control BEFORE I2C scan
    # This ensures APC1 is powered on even after soft reset
    APC1_SET_PIN, APC1_RESET_PIN = get_apc1_pins(settings)
    apc1_power = APC1Power(set_pin=APC1_SET_PIN, reset_pin=APC1_RESET_PIN)
    
    # Always reset and enable APC1 at boot to handle soft reset case
    print("Initializing APC1 power...")
    apc1_power.enable()
    apc1_power.reset_pulse()
    time.sleep(2)  # Wait 150ms for APC1 to fully power up before I2C scan
    print("APC1 powered on")

    devices = i2c.scan()
    print("I2C scan:", [hex(d) for d in devices])

    apc1_addr = settings.get("apc1", {}).get("address", 18)
    has_apc1 = apc1_addr in devices
    
    if has_apc1:
        print(f"✓ APC1 detected at {hex(apc1_addr)}")
    else:
        print(f"⚠ APC1 not found at {hex(apc1_addr)}")
    has_shtc3 = 0x70 in devices

    apc1 = APC1(i2c, apc1_addr) if has_apc1 else None
    sht = SHTC3(i2c) if has_shtc3 else None
    batt = Battery(adc_pin=26, divider_ratio=2.0)

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

    # Initialize Blynk publisher if enabled
    blynk_publisher = None
    blynk_cfg = get_blynk_settings(settings)
    if blynk_cfg["enabled"]:
        try:
            import blynk_mqtt
            from blynk_publisher import BlynkPublisher

            blynk_publisher = BlynkPublisher(
                sensor_cache=cache,
                blynk_mqtt=blynk_mqtt,
                update_interval_s=blynk_cfg["mqtt_update_interval_s"]
            )
            print(f"Blynk publisher configured (interval: {blynk_cfg['mqtt_update_interval_s']}s)")
        except Exception as e:
            print(f"⚠ Blynk initialization failed: {e}")
            blynk_publisher = None

except Exception as e:
    # Critical initialization error - show on OLED if possible
    import sys
    print("="*40)
    print("INITIALIZATION ERROR:")
    print("="*40)
    sys.print_exception(e)
    print("="*40)
    try:
        if 'oled' in locals():
            oled.fill(0)
            oled.text("INIT ERROR", 0, 0)
            oled.text(str(e)[:20], 0, 16)
            oled.show()
    except:
        pass
    # Don't auto-reset so we can see the error
    print("\n*** HALTED - Please check error above ***")
    while True:
        time.sleep(1)

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


def wake_up(source="physical"):
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
        print(f"Wake-up triggered by: {source}")  # <-- MODIFIED FOR WEBSERVER


# -------- ASYNC TASKS --------

async def display_task():
    """Async task to update display from cached sensor data or menus."""
    print(f"Display task started ({DISPLAY_FPS} FPS)")
    interval_ms = int(1000 / DISPLAY_FPS)

    from screens import draw_settings_menu, draw_mode_selection, draw_reset_confirmation, draw_debug_menu, draw_display_settings
    from config import load_settings, get_operation_mode

    # Wait a moment for initialization to complete before first draw
    await asyncio.sleep_ms(100)

    # Force initial draw
    screen_mgr.needs_redraw = True

    while True:
        try:
            # Check if we're in a submenu
            if screen_mgr.in_submenu:
                # Draw appropriate submenu
                if screen_mgr.submenu_type == "settings":
                    draw_settings_menu(oled, screen_mgr.submenu_index, screen_mgr.scroll_offset)
                elif screen_mgr.submenu_type == "mode_select":
                    # Get current mode for display
                    current_settings = load_settings()
                    current_mode = get_operation_mode(current_settings)
                    draw_mode_selection(oled, screen_mgr.submenu_index, current_mode)
                elif screen_mgr.submenu_type == "reset_confirm":
                    # Draw reset confirmation
                    draw_reset_confirmation(oled, screen_mgr.submenu_index)
                elif screen_mgr.submenu_type == "display_settings":
                    # Draw display timeout settings with mode
                    draw_display_settings(oled, screen_mgr.timeout_value,
                                        screen_mgr.display_timeout_mode,
                                        screen_mgr.timeout_confirm_index)
                elif screen_mgr.submenu_type == "debug":
                    # Draw debug menu
                    draw_debug_menu(oled, screen_mgr.submenu_index)
            else:
                # Check if immediate redraw needed OR regular refresh interval
                if screen_mgr.needs_redraw or screen_mgr.should_refresh():
                    screen_mgr.draw_screen(cache, oled)
                    screen_mgr.mark_refreshed()
                    screen_mgr.needs_redraw = False  # Clear the flag
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
                wake_up("physical")  # <-- MODIFIED FOR WEBSERVER

                # Handle encoder rotation based on current state
                if screen_mgr.in_submenu:
                    # Check if in display settings
                    if screen_mgr.submenu_type == "display_settings":
                        if screen_mgr.display_timeout_mode == "adjusting":
                            # Adjusting mode: modify timeout value
                            if current_val > last_encoder_val:
                                screen_mgr.adjust_timeout_up()
                            else:
                                screen_mgr.adjust_timeout_down()
                        else:
                            # Confirming mode: toggle between Save/Cancel
                            if current_val > last_encoder_val:
                                screen_mgr.timeout_confirm_index = (screen_mgr.timeout_confirm_index + 1) % 2
                            else:
                                screen_mgr.timeout_confirm_index = (screen_mgr.timeout_confirm_index - 1) % 2
                        # Display settings will be redrawn by display_task
                    else:
                        # Navigate menu items
                        if current_val > last_encoder_val:
                            screen_mgr.next_menu_item()
                        else:
                            screen_mgr.prev_menu_item()
                        # Menu will be redrawn by display_task
                else:
                    # Navigate main screens
                    if current_val > last_encoder_val:
                        screen_mgr.next_screen()
                    else:
                        screen_mgr.prev_screen()
                    # Draw screen immediately
                    screen_mgr.draw_screen(cache, oled)

                last_encoder_val = current_val

            # Check button
            if not btn.value():  # Active low
                wake_up("physical")  # <-- MODIFIED FOR WEBSERVER
                action = screen_mgr.handle_button()

                # Handle menu actions
                if action:
                    if isinstance(action, dict):
                        action_type = action.get("type")

                        if action_type == "reset_wifi":
                            # Reset WiFi (write to wifi.json only)
                            from wifi_config import reset_wifi
                            if reset_wifi():
                                show_big(oled, ["Wi-Fi reset!", "Reboot to setup"], [1.5, 1])
                                await asyncio.sleep(2)
                                machine.reset()
                            else:
                                show_big(oled, ["Reset failed!", "Try again"], [1.5, 1])
                                await asyncio.sleep(2)

                        elif action_type == "set_mode":
                            # Set mode (write to runtime.json only)
                            from runtime_state import set_mode
                            new_mode = action.get("mode", "mobile")
                            if set_mode(new_mode):
                                show_big(oled, [f"Mode: {new_mode.upper()}", "Reboot to apply"], [1.5, 1])
                                print(f"Mode set to: {new_mode}")
                                await asyncio.sleep(2)
                                machine.reset()
                            else:
                                show_big(oled, ["Save failed!", "Try again"], [1.5, 1])
                                await asyncio.sleep(2)

                        elif action_type == "timeout_saved":
                            # Timeout was saved, show confirmation briefly
                            timeout_val = action.get("value", 0)
                            if timeout_val == 0:
                                show_big(oled, ["Timeout: Never"], [1.5])
                            else:
                                show_big(oled, [f"Timeout: {timeout_val}s"], [1.5])
                            await asyncio.sleep(1)
                            # Reset idle timer to apply new timeout immediately
                            wake_up("physical")  # <-- MODIFIED FOR WEBSERVER

                        elif action_type == "exit_program":
                            # Exit program gracefully via KeyboardInterrupt
                            oled.fill(0)
                            oled.text("Exiting...", 30, 20)
                            oled.text("Connect to", 20, 32)
                            oled.text("Thonny now", 20, 44)
                            oled.show()
                            print("DEBUG: Exiting program gracefully")
                            await asyncio.sleep(1)
                            raise KeyboardInterrupt

                    # Legacy string action support
                    elif action == "resetwifi":
                        from wifi_config import reset_wifi
                        if reset_wifi():
                            show_big(oled, ["Wi-Fi reset!", "Reboot to setup"], [1.5, 1])
                            await asyncio.sleep(2)
                            machine.reset()

                # Debounce delay
                await asyncio.sleep_ms(200)

        except Exception as e:
            print(f"Input error: {e}")

        await asyncio.sleep_ms(interval_ms)


async def power_mgmt_task(webserver_sessions=None):
    """Async task to manage power states based on inactivity with web awareness.
    
    Args:
        webserver_sessions: WebSessionManager instance for web presence detection
    """
    global display_on, apc1_awake

    # Get initial timeout
    screen_timeout = get_screen_timeout()
    timeout_str = "Never" if screen_timeout == 0 else f"{screen_timeout}s"
    print(f"Power mgmt started (timeout: {timeout_str})")

    while True:
        try:
            # Get current timeout (may have changed via settings)
            screen_timeout = get_screen_timeout()
            idle_time = get_idle_time()

            # Check for active web sessions (if webserver is running)
            web_active = False
            if webserver_sessions:
                web_active = webserver_sessions.has_active_sessions()

            # Display power management (unchanged)
            if screen_timeout > 0 and display_on and idle_time > screen_timeout:
                oled.poweroff()
                display_on = False
                print("Display off")

            # APC1 power management (enhanced for web awareness)
            operation_mode = get_operation_mode(settings)
            if operation_mode == "mobile":
                # In mobile mode, consider web activity
                effective_idle = 0 if web_active else idle_time

                if screen_timeout > 0 and apc1_awake and effective_idle > screen_timeout:
                    apc1_power.disable()
                    apc1_awake = False
                    print("APC1 sleep (mobile mode)")
                elif not apc1_awake and (web_active or effective_idle <= screen_timeout):
                    apc1_power.enable()
                    apc1_awake = True
                    print("APC1 wake (web/mobile activity)")
            # In station mode, APC1 is managed by apc1_station_mode_task

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

async def memory_monitor_task(interval_s=30, threshold_kb=20):
    """Monitor and log free memory periodically.

    Args:
        interval_s: How often to check memory (seconds)
        threshold_kb: Warn if free memory drops below this (KB)
    """
    print(f"Memory monitor started (check every {interval_s}s, threshold: {threshold_kb}KB)")

    while True:
        await asyncio.sleep(interval_s)

        try:
            gc.collect()
            free = gc.mem_free()
            used = gc.mem_alloc()

            free_kb = free / 1024
            used_kb = used / 1024

            print(f"💾 MEM: {free_kb:.1f}KB free / {used_kb:.1f}KB used")

            if free_kb < threshold_kb:
                print(f"⚠ LOW MEMORY! Only {free_kb:.1f}KB free")
                gc.collect()  # Extra GC on low memory
        except Exception as e:
            print(f"Memory monitor error: {e}")


async def wifi_monitor_task(wifi_cfg):
    """Monitor WiFi connection and auto-reconnect if disconnected.

    Args:
        wifi_cfg: WiFi configuration dict with ssid, password, retry_interval_s
    """
    global blynk_publisher

    retry_interval = wifi_cfg["retry_interval_s"]
    ssid = wifi_cfg["ssid"]
    password = wifi_cfg["password"]

    print(f"WiFi monitor started (check every {retry_interval}s)")

    while True:
        await asyncio.sleep(retry_interval)

        try:
            if not wifi_helper.is_connected():
                print("⚠ WiFi disconnected - attempting reconnect...")

                # Try to reconnect
                connected = await wifi_helper.connect_async(ssid, password, timeout_s=15)

                if connected:
                    print("✓ WiFi reconnected!")

                    # Re-enable NTP if configured
                    if ntp_sync and not ntp_sync.is_synced():
                        print("Syncing NTP after WiFi reconnect...")
                        await ntp_sync.sync_time_async()

                    # Re-enable Blynk if configured
                    if blynk_publisher and not blynk_publisher.enabled:
                        print("Re-enabling Blynk after WiFi reconnect...")
                        blynk_publisher.enable()
                else:
                    print("⚠ WiFi reconnect failed - will retry")
            # else: WiFi is connected, all good

        except Exception as e:
            print(f"WiFi monitor error: {e}")


async def ntp_mqtt_recovery_task():
    """Background task to recover NTP and enable MQTT if they failed initially.

    Attempts NTP sync every 5 minutes if not synced.
    Enables Blynk publisher once NTP is available.
    """
    global blynk_publisher

    print("NTP/MQTT recovery task started")

    while True:
        await asyncio.sleep(300)  # Check every 5 minutes

        try:
            # Try to recover NTP if not synced
            if ntp_sync and not ntp_sync.is_synced():
                print("Attempting NTP recovery...")
                if await ntp_sync.sync_time_async():
                    print("✓ NTP recovered!")

                    # Enable Blynk if configured and NTP now available
                    if blynk_publisher and not blynk_publisher.enabled:
                        print("Enabling Blynk publisher...")
                        blynk_publisher.enable()
        except Exception as e:
            print(f"Recovery task error: {e}")


async def main():
    """Main async coordinator - starts all tasks.

    Features graceful degradation:
    - Continues running even if WiFi fails
    - Continues running even if NTP fails
    - Continues running even if MQTT fails
    - Display always works locally
    """
    global blynk_publisher

    print("Starting async tasks...")
    log_memory("Startup")

    # Get WiFi configuration
    wifi_cfg = get_wifi_settings(settings)

    # Aggressive GC before WiFi connection
    gc.collect()
    log_memory("Before WiFi")

    # Connect WiFi at startup (if Blynk or NTP enabled)
    wifi_connected = False
    if blynk_cfg["enabled"] or ntp_cfg["enabled"]:
        print("Connecting to WiFi...")
        try:
            wifi_connected = await wifi_helper.connect_async(
                wifi_cfg["ssid"],
                wifi_cfg["password"],
                timeout_s=15,
                oled=oled
            )
            if wifi_connected:
                print("✓ WiFi connected")
            else:
                print("⚠ WiFi connection failed - continuing local-only")
        except Exception as e:
            print(f"⚠ WiFi error: {e}")
            print("⚠ Continuing local-only")

    # GC after WiFi
    gc.collect()
    log_memory("After WiFi")

    # Try initial NTP sync (only if WiFi connected)
    ntp_available = False
    if ntp_sync and wifi_connected:
        gc.collect()  # GC before NTP
        print("Attempting initial NTP sync...")
        try:
            ntp_available = await ntp_sync.sync_time_async()
            if ntp_available:
                print("✓ NTP synced")
            else:
                print("⚠ NTP sync failed - will retry in background")
        except Exception as e:
            print(f"⚠ NTP sync error: {e}")
            print("⚠ Will retry in background")
        gc.collect()  # GC after NTP
        log_memory("After NTP")
    elif ntp_sync and not wifi_connected:
        print("⚠ NTP disabled (no WiFi)")

    # GC before MQTT initialization
    gc.collect()

    # Enable Blynk publisher (only if WiFi connected and NTP available)
    if blynk_publisher:
        if wifi_connected and ntp_available:
            blynk_publisher.enable()
            print("✓ Blynk publisher enabled")
        else:
            if not wifi_connected:
                print("⚠ Blynk disabled (no WiFi)")
            elif not ntp_available:
                print("⚠ Blynk disabled (waiting for NTP)")

    # Get webserver configuration
    webserver_cfg = get_webserver_settings(settings)

    # Initialize webserver if enabled and WiFi connected
    webserver_sessions = None
    if webserver_cfg["enabled"] and wifi_connected:
        try:
            from lib.webserver import WebServer
            
            # Create webserver instance to get session manager
            webserver = WebServer(cache, apc1_power, wake_up, webserver_cfg)
            webserver_sessions = webserver.sessions
            
            # Inject power states getter
            def get_power_states():
                return {
                    'apc1_awake': apc1_awake,
                    'display_on': display_on
                }
            webserver.get_power_states = get_power_states
            
            print(f"Webserver configured (port: {webserver_cfg['port']})")
        except Exception as e:
            print(f"⚠ Webserver initialization failed: {e}")
            webserver = None
            webserver_sessions = None
    else:
        webserver = None
        webserver_sessions = None
        if webserver_cfg["enabled"]:
            print("⚠ Webserver disabled (no WiFi)")

    # Get operation mode and decide which APC1 task to use
    operation_mode = get_operation_mode(settings)
    print(f"📍 Operation mode: {operation_mode.upper()}")

    # Create core task list (always runs)
    tasks = [
        asyncio.create_task(read_shtc3_task(cache, sht, SHTC3_INTERVAL)),
        asyncio.create_task(read_battery_task(cache, batt, BATTERY_INTERVAL)),
        asyncio.create_task(display_task()),
        asyncio.create_task(input_task()),
        asyncio.create_task(power_mgmt_task(webserver_sessions)),
        asyncio.create_task(screen_update_task()),
    ]

    # Add APC1 task based on operation mode
    if operation_mode == "station":
        # Station mode: Power cycle APC1 periodically
        station_settings = get_station_mode_settings(settings)
        from async_tasks import apc1_station_mode_task
        tasks.append(asyncio.create_task(
            apc1_station_mode_task(cache, apc1, apc1_power, station_settings)
        ))
        print(f"  Using Station mode (APC1 cycles every {station_settings['cycle_period_s']}s)")
    else:
        # Mobile mode: Continuous APC1 reading
        tasks.append(asyncio.create_task(read_apc1_task(cache, apc1, APC1_INTERVAL)))
        print(f"  Using Mobile mode (APC1 reads every {APC1_INTERVAL}s)")

    # Add NTP periodic sync task if enabled and WiFi connected
    if ntp_sync and wifi_connected:
        from ntp_helper import ntp_sync_task
        tasks.append(asyncio.create_task(ntp_sync_task(ntp_sync, initial_sync=False)))
        print("  NTP sync task added")
    elif ntp_sync and not wifi_connected:
        print("  ⚠ NTP task skipped (no WiFi)")

    # Add Blynk MQTT task ONLY if enabled (WiFi + NTP available)
    if blynk_publisher and blynk_publisher.enabled:
        try:
            # Start Blynk publisher task
            tasks.append(asyncio.create_task(blynk_publisher.publish_task()))

            # Start Blynk MQTT connection task
            import blynk_mqtt
            tasks.append(asyncio.create_task(blynk_mqtt.task()))
            print("  Blynk/MQTT tasks added")
        except Exception as e:
            print(f"⚠ Blynk task startup error: {e}")
    elif blynk_publisher and not blynk_publisher.enabled:
        print("  ⚠ Blynk/MQTT tasks skipped (publisher disabled)")

    # Add webserver task if webserver was created
    if webserver:
        try:
            # Start the webserver
            async def webserver_runner():
                await webserver.start()
                # Keep running
                while webserver.running:
                    await asyncio.sleep(1)
            
            tasks.append(asyncio.create_task(webserver_runner()))
            print("  Webserver task added")
        except Exception as e:
            print(f"⚠ Webserver task startup error: {e}")

    # Add memory monitoring task (always runs)
    tasks.append(asyncio.create_task(memory_monitor_task(interval_s=30, threshold_kb=20)))

    # Add WiFi monitoring task (if WiFi features enabled)
    if blynk_cfg["enabled"] or ntp_cfg["enabled"]:
        tasks.append(asyncio.create_task(wifi_monitor_task(wifi_cfg)))

    # Add NTP/MQTT recovery task if either is enabled
    if ntp_sync or blynk_publisher:
        tasks.append(asyncio.create_task(ntp_mqtt_recovery_task()))

    print(f"Started {len(tasks)} async tasks")
    print("=== System Running ===")

    # Wait for all tasks (they run forever)
    # Each task has its own error handling - main loop never crashes
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
