# Blynk MQTT Integration Guide

## Overview

This guide covers integrating Blynk IoT cloud service with your Pico weather station for remote monitoring via MQTT.

## Files Added

- `lib/blynk_mqtt.py` - Blynk MQTT client library
- `lib/umqtt/simple.py` - MQTT protocol implementation
- `blynk_test.py` - **Test script with dummy sensor values**
- Updated `settings.json.example` - Added Blynk configuration
- Updated `lib/config.py` - Added `get_blynk_settings()` helper

## Quick Start - Testing with Dummy Data

### Step 1: Configure settings.json

Edit your `settings.json` with Blynk credentials:

```json
{
  "wifi": {
    "ssid": "YourWiFiSSID",
    "password": "YourWiFiPassword"
  },
  "blynk": {
    "enabled": true,
    "template_id": "TMPL3XHMWZZpP",
    "template_name": "PICO W",
    "auth_token": "YOUR_BLYNK_AUTH_TOKEN_HERE",
    "mqtt_broker": "blynk.cloud",
    "publish_interval_s": 60
  }
}
```

**Get your credentials from:**
1. Log in to https://blynk.cloud
2. Create or select your device template
3. Go to Device Info → Copy the auth token
4. Copy template_id and template_name from device settings

### Step 2: Configure Blynk Dashboard

On https://blynk.cloud, set up these datastreams:

| Datastream Name | Data Type | Min | Max | Units |
|-----------------|-----------|-----|-----|-------|
| Temperature | Double | -40 | 80 | °C |
| Humidity | Double | 0 | 100 | % |
| PM2_5 | Double | 0 | 500 | µg/m³ |

Add widgets to your dashboard:
- **Gauge** or **Label** for Temperature datastream
- **Gauge** or **Label** for Humidity datastream
- **Gauge** or **Label** for PM2_5 datastream

### Step 3: Run Test Script

```bash
# Upload to Pico
# - blynk_test.py
# - lib/blynk_mqtt.py
# - lib/umqtt/simple.py
# - settings.json (with your credentials)

# Run on Pico
>>> import blynk_test
>>> blynk_test.main()
```

**Expected Output:**
```
==================================================
Blynk Test Script - Dummy Sensor Publishing
==================================================

1. Loading configuration...
  Template ID: TMPL3XHMWZZpP
  Template Name: PICO W
  MQTT Broker: blynk.cloud

2. Configuring Blynk MQTT...

3. Connecting to WiFi...
Connecting to WiFi 'YourSSID'... ✓
IP Address: 192.168.1.100

4. Starting Blynk publisher...
==================================================
Press Ctrl+C to stop

✓ MQTT connected to Blynk
Publishing dummy sensor data...
  Temperature = 20-30°C
  Humidity = 40-70%
  PM2_5 = 0-100 µg/m³
Publisher task started
Published: Temp=24.3°C, Humidity=55.2%, PM2.5=42µg/m³
Published: Temp=27.8°C, Humidity=48.9%, PM2.5=67µg/m³
Published: Temp=22.1°C, Humidity=63.4%, PM2.5=28µg/m³
...
```

### Step 4: Verify in Blynk Dashboard

1. Open your Blynk app or web dashboard
2. You should see values updating every 5 seconds
3. Values are random dummy data:
   - Temperature: 20-30°C
   - Humidity: 40-70%
   - PM2.5: 0-100 µg/m³

## Test Script Details

### What It Does
- **Generates dummy sensor values** (no real sensors needed)
- **Publishes to Blynk every 5 seconds** (faster than production for testing)
- **Uses async architecture** (compatible with main_async.py)
- **Validates configuration** before starting
- **Handles WiFi connection** and reconnection

### Datastream Mapping
- **Temperature**: Temperature (°C)
- **Humidity**: Humidity (%)
- **PM2_5**: PM2.5 (µg/m³)

### Dummy Data Ranges
```python
Temperature: random 20-30°C
Humidity: random 40-70%
PM2.5: random 0-100 µg/m³
```

## Troubleshooting

### "Blynk is disabled in settings.json"
→ Set `"blynk.enabled": true` in settings.json

### "Blynk auth_token not configured"
→ Add your auth token from Blynk Device Info

### "WiFi SSID not configured"
→ Add WiFi credentials to settings.json

### "WiFi connection timeout"
→ Check WiFi SSID/password, ensure network is available

### "MQTT disconnected"
→ Check auth_token, ensure device is online in Blynk dashboard

### No data in Blynk dashboard
→ Verify datastreams (Temperature, Humidity, PM2_5) are configured correctly

## Next Steps

Once the test script works:

1. ✅ **Verify connectivity** - Test script publishes dummy data
2. ✅ **Configure dashboard** - Set up widgets and datastreams
3. ⏳ **Integrate with real sensors** - Modify to use actual sensor_cache data
4. ⏳ **Add to main_async.py** - Create async Blynk publisher task
5. ⏳ **Adjust intervals** - Change publish_interval_s to 60s for production

## Integration with main_async.py (Future)

After testing, we'll create:
- `lib/blynk_publisher.py` - Async task to publish real sensor data
- Modify `main_async.py` - Add Blynk publisher task
- Read from `sensor_cache` instead of dummy values
- Configure production publish interval (60s default)

## Configuration Reference

### settings.json Blynk Section

```json
"blynk": {
  "enabled": false,              // Set to true to enable
  "template_id": "",             // From Blynk Device Info
  "template_name": "",           // From Blynk Device Info
  "auth_token": "",              // From Blynk Device Info
  "mqtt_broker": "blynk.cloud",  // Usually don't need to change
  "publish_interval_s": 60       // How often to publish (seconds)
}
```

### WiFi Configuration (Existing)

```json
"wifi": {
  "ssid": "YourNetworkName",
  "password": "YourPassword"
}
```

**Note:** WiFi credentials are shared system-wide, not duplicated in Blynk config.

## Architecture

```
┌─────────────────────────────────────────────────┐
│           blynk_test.py (Test)                  │
├─────────────────────────────────────────────────┤
│                                                 │
│  ┌──────────────┐      ┌─────────────┐         │
│  │ WiFi Connect │─────→│ Blynk MQTT  │         │
│  └──────────────┘      └──────┬──────┘         │
│                               │                 │
│  ┌──────────────┐            │                 │
│  │ Dummy Values │────────────┘                 │
│  │ Temperature  │  Publish every 5s            │
│  │ Humidity     │  via datastreams:            │
│  │ PM2_5        │  ds/Temperature              │
│  └──────────────┘  ds/Humidity                 │
│                    ds/PM2_5                     │
│           ↓                                     │
│     Blynk.Cloud                                 │
│     Dashboard                                   │
└─────────────────────────────────────────────────┘
```

## Support

- Blynk Documentation: https://docs.blynk.io
- Community Forum: https://community.blynk.cc
- Weather Station Repo: Check README.md for project details
