# Configuration Files Architecture

This project uses a three-file configuration system to separate concerns and prevent runtime corruption of static settings.

## File Structure

```
/
├── settings.json          # Static config (user edits manually)
├── wifi.json             # WiFi credentials (auto-created, can be reset)
├── runtime.json          # Runtime state (auto-created, UI changes)
├── settings.json.example # Template for settings.json
├── wifi.json.example     # Template for wifi.json
└── runtime.json.example  # Template for runtime.json
```

---

## 1. settings.json (Static Configuration)

**Purpose:** Hardware configuration, sensor settings, API keys, and defaults

**Modified by:** User edits manually (never by code at runtime)

**Note:** WiFi credentials are NOT stored here - they belong in wifi.json

**Example:**
```json
{
  "default_mode": "mobile",
  "station_mode": {
    "cycle_period_s": 300,
    "warmup_time_s": 60,
    "read_delay_ms": 100
  },
  "i2c": {"sda": 16, "scl": 17},
  "apc1": {
    "address": 18,
    "set_pin": 22,
    "reset_pin": 21
  },
  "power": {
    "display_sleep_s": 30,
    "apc1_sleep_s": 300
  },
  "sensors": {
    "shtc3_interval_s": 5,
    "apc1_interval_s": 10,
    "battery_interval_s": 15
  },
  "display": {
    "refresh_fps": 5,
    "input_poll_hz": 20
  },
  "blynk": {
    "enabled": false,
    "template_id": "",
    "template_name": "",
    "auth_token": "",
    "mqtt_broker": "blynk.cloud",
    "mqtt_update_interval_s": 30
  },
  "ntp": {
    "enabled": true,
    "servers": ["pool.ntp.org", "time.google.com"],
    "timezone_offset_hours": 5.5,
    "sync_interval_s": 3600
  }
}
```

**Managed by:**
- User manually edits this file
- Code only reads from it (never writes)

---

## 2. wifi.json (WiFi Credentials) - REQUIRED

**Purpose:** WiFi network credentials that can be safely reset via UI

**Modified by:** 
- WiFi setup AP (when configuring WiFi)
- "Reset WiFi" menu action
- Code at runtime (safe to write)

**Auto-created:** 
- On first WiFi setup via AP mode
- When user manually creates the file

**Example:**
```json
{
  "ssid": "YourWiFiSSID",
  "password": "YourWiFiPassword",
  "retry_interval_s": 60
}
```

**Managed by:**
- `lib/wifi_config.py` module
- `boot.py` during WiFi setup
- Menu action "Reset WiFi"

**Behavior:**
- **Required file** - Code reads WiFi credentials ONLY from this file
- If missing or empty → Triggers AP mode for WiFi setup
- Reset WiFi → Clears this file, triggers AP mode on reboot
- No fallback to settings.json

---

## 3. runtime.json (Runtime State)

**Purpose:** Current operating mode selected via UI

**Modified by:**
- "Select Mode" menu action
- Code at runtime (safe to write)

**Auto-created:**
- When user first selects a mode via Settings menu

**Example:**
```json
{
  "mode": "station"
}
```

**Possible values:**
- `"mode": "mobile"` - Continuous APC1 reading (default)
- `"mode": "station"` - Power-cycled APC1 reading

**Managed by:**
- `lib/runtime_state.py` module
- Menu action "Select Mode"

**Behavior:**
- If missing, falls back to settings.json "default_mode" field
- If "default_mode" not in settings.json, uses hardcoded "mobile"
- Mode selection → Updates this file only (settings.json untouched)

---

## Architecture Design

### Clean Separation of Concerns
```
settings.json  ← Static config (read-only for code)
wifi.json     ← WiFi credentials (code can write safely, REQUIRED)
runtime.json  ← Runtime state (code can write safely, optional)
```

**Key Principles:**
- settings.json is NEVER modified by code at runtime
- wifi.json is REQUIRED - missing/empty triggers AP mode
- runtime.json is optional - falls back to default_mode
- Each file has a single, clear responsibility

---

## Benefits

### Safety
✅ settings.json never corrupted by runtime writes
✅ WiFi reset safe - only affects wifi.json
✅ Mode changes safe - only affects runtime.json
✅ Smaller files = less risk of partial writes

### Maintainability
✅ Clear separation of concerns
✅ Easy debugging - know where each setting comes from
✅ Clean architecture - single responsibility per file

### Flexibility
✅ Recoverable - corrupt wifi/runtime files just regenerate
✅ Extensible - easy to add more runtime state
✅ Portable - copy settings.json between devices safely

---

## File Lifecycle

### First Boot (New Install)
```
1. No files exist
2. boot.py → wifi.json returns empty credentials
3. Triggers WiFi setup AP
4. User configures WiFi
5. Creates wifi.json ✅
6. Runs with default mode (mobile)
```

### Mode Selection (First Time)
```
1. User navigates to Settings → Select Mode
2. Chooses "Station"
3. Code calls runtime_state.set_mode("station")
4. Creates runtime.json with {"mode": "station"} ✅
5. Reboots
6. Station mode active
```

### Reset WiFi
```
1. User navigates to Settings → Reset WiFi
2. Code calls wifi_config.reset_wifi()
3. Writes empty credentials to wifi.json ✅
4. Reboots
5. Triggers WiFi setup AP
```

---

## Development Notes

### To manually set WiFi on device:
```json
# Create wifi.json with:
{
  "ssid": "YourNetwork",
  "password": "YourPassword",
  "retry_interval_s": 60
}
```

### To manually set mode on device:
```json
# Create runtime.json with:
{
  "mode": "station"
}
# or
{
  "mode": "mobile"
}
```

### To reset to defaults:
```bash
# Delete files to force regeneration
rm wifi.json      # Triggers WiFi setup
rm runtime.json   # Uses default_mode from settings.json
```

---

## Code References

**WiFi Management:**
- `lib/wifi_config.py` - WiFi credential management
- `boot.py` - WiFi setup and migration logic
- `lib/config.py` - `get_wifi_settings()` reads wifi.json

**Mode Management:**
- `lib/runtime_state.py` - Runtime state management
- `lib/config.py` - `get_operation_mode()` reads runtime.json
- `main_async.py` - Menu actions call set_mode()

**Menu Actions:**
- Settings → Reset WiFi → `wifi_config.reset_wifi()`
- Settings → Select Mode → `runtime_state.set_mode()`
