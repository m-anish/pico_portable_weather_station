"""async_tasks.py
Async task definitions for sensor reading and display management.

Provides uasyncio tasks that run independently to read sensors and
update the display without blocking each other.
"""

try:
    import uasyncio as asyncio
except ImportError:
    import asyncio
import time


async def read_shtc3_task(cache, sht, interval_s=5):
    """Background task to read SHTC3 temperature/humidity sensor.
    
    Args:
        cache: SensorCache instance
        sht: SHTC3 sensor instance (or None if not available)
        interval_s: Read interval in seconds
    """
    if sht is None:
        return
    
    print(f"SHTC3 task started (interval: {interval_s}s)")
    
    while True:
        try:
            # Read sensor (blocking I2C operation)
            temp, humid = sht.measure()
            # Update cache (thread-safe)
            cache.update_shtc3(temp, humid)
            if temp is not None:
                print(f"SHTC3: {temp:.1f}°C, {humid:.1f}%")
        except Exception as e:
            print(f"SHTC3 read error: {e}")
            # Update cache with None to indicate error
            cache.update_shtc3(None, None)
        
        # Sleep until next reading
        await asyncio.sleep(interval_s)


async def read_apc1_task(cache, apc1, interval_s=10):
    """Background task to read APC1 air quality sensor.
    
    Args:
        cache: SensorCache instance
        apc1: APC1 sensor instance (or None if not available)
        interval_s: Read interval in seconds
    """
    if apc1 is None:
        return
    
    print(f"APC1 task started (interval: {interval_s}s)")
    
    while True:
        try:
            # Read all sensor values (blocking I2C operation)
            readings = apc1.read_all()
            # Update cache (thread-safe)
            cache.update_apc1(readings)
            if readings:
                pm25 = readings.get('PM2.5', {}).get('value')
                if pm25 is not None:
                    print(f"APC1: PM2.5={pm25:.0f} µg/m³")
        except Exception as e:
            print(f"APC1 read error: {e}")
            # Update cache with None to indicate error
            cache.update_apc1(None)
        
        # Sleep until next reading
        await asyncio.sleep(interval_s)


async def read_battery_task(cache, batt, interval_s=15):
    """Background task to read battery voltage and percentage.
    
    Args:
        cache: SensorCache instance
        batt: Battery instance (or None if not available)
        interval_s: Read interval in seconds
    """
    if batt is None:
        return
    
    print(f"Battery task started (interval: {interval_s}s)")
    
    while True:
        try:
            # Read battery (ADC operation)
            voltage = batt.read_voltage()
            percent = batt.read_percentage()
            # Update cache (thread-safe)
            cache.update_battery(voltage, percent)
            if voltage is not None:
                print(f"Battery: {voltage:.2f}V ({percent:.0f}%)")
        except Exception as e:
            print(f"Battery read error: {e}")
            # Update cache with None to indicate error
            cache.update_battery(None, None)
        
        # Sleep until next reading
        await asyncio.sleep(interval_s)


async def apc1_station_mode_task(cache, apc1, apc1_power, station_settings):
    """Station mode: Power cycle APC1 sensor periodically to save power.
    
    In station mode, the APC1 sensor is normally OFF to conserve power.
    Periodically (e.g., every 5 minutes), the system:
    1. Powers on APC1
    2. Waits for warmup (e.g., 60 seconds)
    3. Reads sensor data
    4. Publishes data (if WiFi/MQTT enabled)
    5. Powers off APC1
    
    Args:
        cache: SensorCache instance
        apc1: APC1 sensor instance (or None if not available)
        apc1_power: APC1Power instance for power control
        station_settings: Dict with cycle_period_s, warmup_time_s, read_delay_ms
    """
    if apc1 is None:
        print("Station mode: APC1 not available, task exiting")
        return
    
    cycle_period = station_settings["cycle_period_s"]
    warmup_time = station_settings["warmup_time_s"]
    read_delay_ms = station_settings["read_delay_ms"]
    
    print(f"Station mode task started")
    print(f"  Cycle period: {cycle_period}s ({cycle_period/60:.1f} min)")
    print(f"  Warmup time: {warmup_time}s")
    
    # Initial shutdown after boot
    apc1_power.disable()
    print("Station mode: APC1 powered OFF (initial state)")
    
    while True:
        # Sleep for the cycle period
        await asyncio.sleep(cycle_period)
        
        # Wake up APC1
        apc1_power.enable()
        print(f"Station mode: APC1 powered ON (warming up for {warmup_time}s)")
        
        # Wait for sensor warmup
        await asyncio.sleep(warmup_time)
        
        # Read sensor
        try:
            readings = apc1.read_all()
            cache.update_apc1(readings)
            
            if readings:
                pm25 = readings.get('PM2.5', {}).get('value')
                pm10 = readings.get('PM10', {}).get('value')
                print(f"Station mode: Read APC1 - PM2.5={pm25:.0f}, PM10={pm10:.0f} µg/m³")
            else:
                print("Station mode: APC1 read returned no data")
        except Exception as e:
            print(f"Station mode: APC1 read error: {e}")
            cache.update_apc1(None)
        
        # Small delay before shutting down
        await asyncio.sleep_ms(read_delay_ms)
        
        # Power off APC1
        apc1_power.disable()
        print(f"Station mode: APC1 powered OFF (sleeping for {cycle_period}s)")


async def display_update_task(cache, oled, screen_manager, fps=20):
    """Background task to update the display from cached sensor data.
    
    Args:
        cache: SensorCache instance
        oled: SSD1306 display instance
        screen_manager: Object with current_screen, draw_screen, step_scroll methods
        fps: Target frames per second for display updates
    """
    print(f"Display task started (fps: {fps})")
    
    interval_ms = int(1000 / fps)
    
    while True:
        try:
            screen_name = screen_manager.get_current_screen_name()
            
            # Handle scrolling screen separately (needs continuous updates)
            if screen_name == "scroll":
                # Step the scrolling marquee
                screen_manager.step_scroll(cache, oled)
                oled.show()
            else:
                # Regular screen refresh based on interval
                if screen_manager.should_refresh():
                    screen_manager.draw_screen(cache, oled)
                    screen_manager.mark_refreshed()
        except Exception as e:
            print(f"Display update error: {e}")
        
        # Sleep for frame interval
        await asyncio.sleep_ms(interval_ms)


async def input_handler_task(encoder, button, screen_manager, wake_callback, poll_hz=50):
    """Background task to handle encoder and button input.
    
    Args:
        encoder: RotaryIRQ encoder instance
        button: Pin instance for button
        screen_manager: Object with next_screen, prev_screen, handle_button methods
        wake_callback: Function to call when user input detected
        poll_hz: Polling frequency in Hz
    """
    print(f"Input task started (poll rate: {poll_hz}Hz)")
    
    interval_ms = int(1000 / poll_hz)
    last_encoder_val = encoder.value()
    
    while True:
        try:
            # Check encoder
            current_val = encoder.value()
            if current_val != last_encoder_val:
                wake_callback()  # Wake up display/sensors
                
                if current_val > last_encoder_val:
                    screen_manager.next_screen()
                else:
                    screen_manager.prev_screen()
                
                last_encoder_val = current_val
            
            # Check button
            if not button.value():  # Active low
                wake_callback()  # Wake up display/sensors
                screen_manager.handle_button()
                # Debounce delay
                await asyncio.sleep_ms(200)
        
        except Exception as e:
            print(f"Input handler error: {e}")
        
        # Sleep for polling interval
        await asyncio.sleep_ms(interval_ms)


async def power_management_task(display, apc1_power, get_idle_time, 
                                display_sleep_s=30, apc1_sleep_s=300):
    """Background task to manage power states based on inactivity.
    
    Args:
        display: Display object with poweron/poweroff methods
        apc1_power: APC1Power instance for sensor power control
        get_idle_time: Function that returns current idle time in seconds
        display_sleep_s: Seconds before display sleeps
        apc1_sleep_s: Seconds before APC1 sleeps
    """
    print(f"Power mgmt started (display: {display_sleep_s}s, apc1: {apc1_sleep_s}s)")
    
    display_on = True
    apc1_awake = True
    
    while True:
        try:
            idle_time = get_idle_time()
            
            # Display power management
            if display_on and idle_time > display_sleep_s:
                display.poweroff()
                display_on = False
                print("Display off")
            elif not display_on and idle_time <= display_sleep_s:
                display.poweron()
                display_on = True
                print("Display on")
            
            # APC1 power management
            if apc1_awake and idle_time > apc1_sleep_s:
                apc1_power.disable()
                apc1_awake = False
                print("APC1 sleep")
            elif not apc1_awake and idle_time <= apc1_sleep_s:
                apc1_power.enable()
                apc1_awake = True
                print("APC1 wake")
        
        except Exception as e:
            print(f"Power management error: {e}")
        
        # Check power state every 5 seconds
        await asyncio.sleep(5)
