# Webserver Integration Guide

This guide explains how to integrate the webserver into the existing `main_async.py`.

## Files Created

- `lib/webserver.py` - Complete webserver implementation ✅
- `lib/config.py` - Updated with `get_webserver_settings()` function ✅

## Manual Integration Steps

### Step 1: Add Webserver Import

In `main_async.py`, add `get_webserver_settings` to the config imports (around line 30):

```python
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
    get_webserver_settings,  # <-- ADD THIS LINE
)
```

### Step 2: Update `wake_up()` Function

Modify the `wake_up()` function to accept a source parameter (around line 209):

```python
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
        print(f"Wake-up triggered by: {source}")  # <-- MODIFIED THIS LINE
```

### Step 3: Enhance `power_mgmt_task()` for Web Awareness

Replace the existing `power_mgmt_task()` function (around line 288) with this web-aware version:

```python
async def power_mgmt_task():
    """Async task to manage power states based on inactivity with web awareness."""
    global display_on, apc1_awake
    
    # Import webserver module to check for active sessions
    webserver_sessions = None
    
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
```

### Step 4: Add Webserver Initialization in `main()`

In the `main()` async function, after the Blynk initialization section (around line 600), add:

```python
    # Get webserver configuration
    webserver_cfg = get_webserver_settings(settings)
    
    # Initialize webserver if enabled and WiFi connected
    if webserver_cfg["enabled"] and wifi_connected:
        try:
            from webserver import WeatherWebServer
            
            # Create webserver instance
            webserver = WeatherWebServer(cache, wake_up)
            webserver.configure(
                port=webserver_cfg["port"],
                session_timeout=webserver_cfg["session_timeout_s"],
                chunk_size=webserver_cfg["chunk_size"]
            )
            print(f"Webserver configured (port: {webserver_cfg['port']})")
        except Exception as e:
            print(f"⚠ Webserver initialization failed: {e}")
            webserver = None
    else:
        webserver = None
        if webserver_cfg["enabled"]:
            print("⚠ Webserver disabled (no WiFi)")
```

### Step 5: Add Webserver Task

In the task list section (around line 680), add the webserver task:

```python
    # Add webserver task if enabled
    if webserver:
        tasks.append(asyncio.create_task(webserver.run()))
        print("  Webserver task added")
```

### Step 6: Update `settings.json.example`

Add webserver configuration to the example settings file:

```json
{
  "webserver": {
    "enabled": true,
    "port": 80,
    "session_timeout_s": 300,
    "refresh_interval_s": 10,
    "max_connections": 2,
    "response_timeout_s": 30,
    "chunk_size": 512
  }
}
```

## Configuration Options

All webserver settings are in `settings.json`:

- `enabled`: Enable/disable webserver (default: true)
- `port`: HTTP port to listen on (default: 80)
- `session_timeout_s`: Web session timeout in seconds (default: 300)
- `refresh_interval_s`: Auto-refresh interval on web page (default: 10)
- `max_connections`: Maximum concurrent connections (default: 2)
- `response_timeout_s`: HTTP response timeout (default: 30)
- `chunk_size`: HTTP chunk size for responses (default: 512)

## Features

✅ Async HTTP server with chunked responses  
✅ Real-time sensor data display  
✅ System information (uptime, memory, WiFi)  
✅ Mobile-responsive design  
✅ Auto-refresh with JavaScript  
✅ JSON API endpoints  
✅ APC1 wake/sleep control  
✅ Session management with heartbeat  
✅ Power management integration  
✅ Minimal RAM usage with chunked streaming  

## API Endpoints

- `GET /` - Main dashboard page
- `GET /api/data` - JSON sensor data
- `GET /api/system` - JSON system info
- `POST /api/wake` - Wake APC1 sensor
- `POST /api/heartbeat` - Keep session alive

## Testing

1. Set `"enabled": true` in webserver config
2. Ensure WiFi is configured
3. Run `main_async.py`
4. Access `http://<pico-ip-address>` in browser
5. Monitor serial output for webserver logs

## Memory Optimization

The webserver uses several memory optimizations:
- Chunked HTTP responses (512 bytes at a time)
- Generator-based HTML streaming
- Session cleanup (5-minute timeout)
- Connection limits (max 2 simultaneous)
- Aggressive garbage collection
