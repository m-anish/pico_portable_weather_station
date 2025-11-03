# NTP Time Synchronization Integration

## Overview

The weather station now includes centralized NTP (Network Time Protocol) time synchronization with timezone support. This is **critical** for:

1. **SSL/TLS certificate validation** (required for Blynk and other cloud services)
2. **Accurate data timestamps** for sensor logging
3. **Display of correct local time**
4. **Future cloud service integrations**

## Features

✅ **Configurable NTP servers** - Use your preferred time servers  
✅ **Timezone support** - Hours-based offset (e.g., +5.5 for India IST)  
✅ **Async-friendly** - Non-blocking time sync  
✅ **Automatic retry** - Handles network failures gracefully  
✅ **Periodic re-sync** - Keeps time accurate over long runs  
✅ **System-wide** - Available to all modules  

## Quick Start

### 1. Configure settings.json

Edit your `settings.json` with NTP configuration:

```json
{
  "ntp": {
    "enabled": true,
    "servers": ["pool.ntp.org", "time.google.com"],
    "timezone_offset_hours": 5.5,
    "sync_interval_s": 3600
  }
}
```

### 2. Sync happens automatically

When you run `main_async.py`:
1. **Initial sync** at startup (before Blynk/SSL connections)
2. **Periodic re-sync** every hour (configurable)
3. **Available to all modules** via `ntp_sync` instance

## Configuration Reference

### NTP Settings in settings.json

```json
"ntp": {
  "enabled": true,                      // Enable/disable NTP sync
  "servers": ["pool.ntp.org"],          // List of NTP servers to try
  "timezone_offset_hours": 5.5,         // Your timezone offset from UTC
  "sync_interval_s": 3600               // Re-sync interval (3600 = 1 hour)
}
```

### Timezone Examples

| Location | Timezone | Offset | Config Value |
|----------|----------|--------|--------------|
| **India** (IST) | UTC+5:30 | +5.5 | `5.5` |
| **US Eastern** (EST) | UTC-5:00 | -5.0 | `-5.0` |
| **US Pacific** (PST) | UTC-8:00 | -8.0 | `-8.0` |
| **UK** (GMT) | UTC+0:00 | 0.0 | `0.0` |
| **Japan** (JST) | UTC+9:00 | +9.0 | `9.0` |
| **Australia Sydney** | UTC+10:00 | +10.0 | `10.0` |
| **Germany** (CET) | UTC+1:00 | +1.0 | `1.0` |
| **China** (CST) | UTC+8:00 | +8.0 | `8.0` |
| **Brazil** (BRT) | UTC-3:00 | -3.0 | `-3.0` |
| **Nepal** | UTC+5:45 | +5.75 | `5.75` |

**Note:** Fractional hours work! (e.g., 5.5 = 5 hours 30 minutes, 5.75 = 5 hours 45 minutes)

## Architecture

### System Flow

```
main_async.py startup:
  ↓
  1. WiFi connect
  ↓
  2. NTP sync (FIRST - before SSL!)
  ↓
  3. Start Blynk task (now has valid time for SSL)
  ↓
  4. Start sensor tasks
  ↓
  5. Start display tasks
  ↓
  6. NTP periodic re-sync task (hourly)
```

### Components

```
lib/ntp_helper.py
  ├─ NTPSync class
  │   ├─ sync_time() - Synchronous sync
  │   ├─ sync_time_async() - Async sync with retry
  │   ├─ get_local_time() - Get time with timezone offset
  │   └─ get_local_time_str() - Formatted local time string
  └─ ntp_sync_task() - Background periodic sync task

main_async.py
  ├─ Initializes NTPSync from settings
  ├─ Performs initial sync before starting tasks
  └─ Adds periodic re-sync task to event loop

lib/blynk_mqtt.py
  └─ Uses NTP sync for SSL certificate validation
```

## Usage Examples

### In Your Code

```python
from config import load_settings, get_ntp_settings
from ntp_helper import NTPSync

# Load configuration
settings = load_settings()
ntp_cfg = get_ntp_settings(settings)

# Create NTP sync instance
ntp_sync = NTPSync(
    servers=ntp_cfg["servers"],
    timezone_offset_hours=ntp_cfg["timezone_offset_hours"],
    sync_interval_s=ntp_cfg["sync_interval_s"]
)

# Perform sync
await ntp_sync.sync_time_async()

# Get local time
local_time_str = ntp_sync.get_local_time_str()
print(f"Local time: {local_time_str}")
# Output: "Mon 2024-11-03 17:24:13"

# Check if synced
if ntp_sync.is_synced():
    print("Time is synced!")
```

### Getting Time

```python
# Get local time as tuple
local_time = ntp_sync.get_local_time()
year, month, day, hour, minute, second, weekday, yearday = local_time

# Get formatted string
time_str = ntp_sync.get_local_time_str()
print(time_str)
# "Mon 2024-11-03 17:24:13"
```

## Troubleshooting

### "NTP sync failed"
**Causes:**
- No WiFi connection
- NTP servers unreachable
- Firewall blocking NTP (port 123)

**Solutions:**
1. Check WiFi connection
2. Try different NTP servers:
   ```json
   "servers": ["time.nist.gov", "time.cloudflare.com", "0.pool.ntp.org"]
   ```
3. Increase retry attempts in code

### Time is Wrong

**Check timezone offset:**
```json
"timezone_offset_hours": 5.5  // India IST = UTC+5:30
```

**Verify with:**
```python
print(f"Timezone: UTC{ntp_sync._format_offset()}")
print(f"Local time: {ntp_sync.get_local_time_str()}")
```

### SSL Certificate Errors with Blynk

**This means NTP sync failed or time is still invalid.**

**Solution:**
1. Ensure NTP is enabled in settings.json
2. Check NTP sync logs at startup
3. Verify system time is after Jan 2024

## NTP Server Options

### Recommended Servers

**Global:**
- `pool.ntp.org` - Global pool (recommended)
- `time.google.com` - Google's public NTP
- `time.cloudflare.com` - Cloudflare's public NTP
- `time.nist.gov` - NIST (US government)

**Regional:**
- **Asia:** `asia.pool.ntp.org`
- **Europe:** `europe.pool.ntp.org`
- **North America:** `north-america.pool.ntp.org`
- **Oceania:** `oceania.pool.ntp.org`

**Country-specific:**
- **India:** `in.pool.ntp.org`
- **US:** `us.pool.ntp.org`
- **UK:** `uk.pool.ntp.org`
- **Germany:** `de.pool.ntp.org`

### Configuration Example

```json
"ntp": {
  "enabled": true,
  "servers": [
    "in.pool.ntp.org",      // Try India pool first
    "asia.pool.ntp.org",    // Fallback to Asia
    "pool.ntp.org"          // Global fallback
  ],
  "timezone_offset_hours": 5.5,
  "sync_interval_s": 3600
}
```

## Advanced Features

### Manual Sync

```python
# Sync now (blocking)
success = ntp_sync.sync_time(timeout=10)

# Async sync with retry
success = await ntp_sync.sync_time_async(
    timeout=5,
    retry_delay=5,
    max_retries=3
)
```

### Check Sync Status

```python
# Is time synced?
if ntp_sync.is_synced():
    print("Time synchronized")

# Time since last sync
seconds = ntp_sync.time_since_sync()
print(f"Synced {seconds}s ago")

# Does it need re-sync?
if ntp_sync.needs_resync():
    await ntp_sync.sync_time_async()
```

### Custom Periodic Task

```python
from ntp_helper import ntp_sync_task

# Add to your async tasks
async def main():
    tasks = [
        # ... other tasks ...
        asyncio.create_task(ntp_sync_task(ntp_sync, initial_sync=True))
    ]
    await asyncio.gather(*tasks)
```

## Integration with Other Modules

### Using NTP Time for Logging

```python
# In your sensor logging code
timestamp = ntp_sync.get_local_time_str()
log_entry = f"{timestamp}, Temp: {temp}°C, Humidity: {humidity}%"
```

### Using with Blynk

NTP sync is **automatically integrated** with Blynk in `lib/blynk_mqtt.py`:
- Syncs time before SSL connection
- Required for SSL certificate validation
- No additional code needed!

## Files

**Created:**
- ✅ `lib/ntp_helper.py` - NTP sync module with timezone support
- ✅ `NTP_INTEGRATION.md` - This documentation

**Modified:**
- ✅ `settings.json.example` - Added NTP configuration
- ✅ `lib/config.py` - Added `get_ntp_settings()` helper
- ✅ `main_async.py` - Added NTP initialization and periodic sync task
- ✅ `lib/blynk_mqtt.py` - Integrated NTP sync for SSL connections

## Benefits

1. **System-wide time sync** - All modules can use accurate time
2. **SSL certificate validation** - Required for secure connections
3. **Accurate timestamps** - For data logging and display
4. **Timezone support** - Display local time correctly
5. **Async-friendly** - Non-blocking, cooperative multitasking
6. **Configurable** - Servers, timezone, sync interval in settings.json
7. **Automatic** - Syncs at startup and periodically

## Summary

You now have a complete NTP time synchronization system that:
- ✅ Syncs time at startup (before SSL connections)
- ✅ Re-syncs periodically to maintain accuracy
- ✅ Supports custom timezone offsets
- ✅ Works with multiple NTP servers (fallback support)
- ✅ Integrates with Blynk for SSL certificate validation
- ✅ Available system-wide for logging and timestamps

**Just configure your timezone in settings.json and it works!** 🎉
