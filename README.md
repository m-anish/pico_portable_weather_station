# Pico Portable Weather Station

A comprehensive portable environmental monitoring station for Raspberry Pi Pico W with MicroPython. Features real-time display of temperature, humidity, air quality (PM2.5/PM10), AQI calculations, and battery monitoring with intelligent power management.

## Features

- **Multi-Sensor Support**: APC1 air quality sensor + SHTC3 temperature/humidity sensor
- **Air Quality Index (AQI)**: EPA-standard AQI calculation from PM2.5 data
- **Interactive OLED Display**: 128x64 SSD1306 with rotary encoder navigation
- **Power Management**: Configurable sleep modes for display and sensors
- **Battery Monitoring**: Real-time voltage and percentage with Li-Ion estimation
- **WiFi Configuration**: Built-in access point for easy wireless setup
- **Multiple Display Screens**:
  - Temperature & Humidity
  - Particulate Matter (PM2.5/PM10)
  - Air Quality Index (AQI)
  - Battery Status
  - Scrolling summary of all readings
  - WiFi reset utility

## Hardware Requirements

- Raspberry Pi Pico W (with wireless capabilities)
- MicroPython firmware (tested with v1.20+)
- 0.96" I2C OLED Display (SSD1306, 128x64)
- Sensirion SHTC3 Temperature/Humidity Sensor
- Sciosense APC1 Air Quality Sensor (I2C version)
- EC11 Rotary Encoder with push button
- Li-Ion battery with TP4056 charging module
- Connecting wires and breadboard

## Hardware Wiring

### I2C Bus (SDA: GP16, SCL: GP17)
- SHTC3 Sensor → I2C bus (default address: 0x70)
- APC1 Sensor → I2C bus (default address: 0x12)
- SSD1306 OLED → I2C bus (address: 0x3C)

### Rotary Encoder
- A (CLK): GP18
- B (DT): GP19
- C (SW/button): GP20 (with pull-up)

### APC1 Power Control
- SET: GP22 (active high for enable, low for sleep)
- RST: GP21 (active low reset)

### Battery Monitoring
- Battery positive → VSYS pin (for power)
- Voltage divider (0.5 ratio) → GP26 (ADC0)
  - R1: 10kΩ (to battery+)
  - R2: 10kΩ (to GND)

### Power Management
- Battery switch controls main power
- Micro-USB for development (disconnect battery when using USB)

## Software Setup

### 1. Install MicroPython
1. Download MicroPython UF2 for Pico W from [micropython.org](https://micropython.org/download/rp2-pico-w/)
2. Put Pico into bootloader mode (hold BOOTSEL while plugging in)
3. Drag UF2 file to RPI-RP2 drive

### 2. Upload Project Files
1. Copy all files from this repository to your Pico
2. Ensure `lib/` directory and all subdirectories are uploaded
3. The project uses `settings.json` for configuration (auto-created on first run)

### 3. Initial Configuration
1. Power on the device
2. If no WiFi configured, it will create an access point
3. Connect to `PICO_SETUP` network (password: `12345678`)
4. Open browser to `192.168.4.1` and configure your WiFi

## Configuration

The device uses `settings.json` for configuration. Default settings:

```json
{
  "i2c": {
    "sda": 16,
    "scl": 17
  },
  "power": {
    "display_sleep_s": 30,
    "apc1_sleep_s": 300
  },
  "apc1": {
    "address": 18,
    "set_pin": 22,
    "reset_pin": 21
  }
}
```

### Configuration Options
- `i2c.sda/scl`: I2C pin assignments
- `power.display_sleep_s`: Seconds before display turns off (0 = never)
- `power.apc1_sleep_s`: Seconds before APC1 sensor sleeps (0 = never)
- `apc1.*`: APC1 sensor configuration

## Usage

### Navigation
- **Rotate**: Cycle through screens
- **Press Button**: Wake from sleep or interact with current screen
- **Hold Button on Startup**: Enter debug mode (exits main.py)

### Screens
1. **Temp & Humidity**: Current temperature and humidity readings
2. **Particles**: PM2.5 and PM10 concentrations
3. **AQI**: Air Quality Index with EPA breakpoints
4. **Battery**: Voltage and estimated percentage
5. **All Readings**: Scrolling summary of all sensor data
6. **Reset WiFi**: Clear WiFi settings (reboot required)

### Power Management
- Display sleeps after configurable idle time
- APC1 sensor enters deep sleep when not in use
- Rotary encoder activity wakes the device
- Button press wakes from sleep

## Sensor Calibration

### APC1 Air Quality Sensor
- Factory calibrated, no user calibration needed
- AQI calculation follows EPA 24-hour PM2.5 breakpoints

### SHTC3 Temperature/Humidity
- Factory calibrated
- Readings accurate to ±0.2°C / ±0.9%RH

### Battery Monitoring
- Voltage divider ratio: 0.5 (configurable in `battery.py`)
- Li-Ion discharge curve estimation
- Accuracy: ±0.1V voltage, ±5% percentage

## Troubleshooting

### Device Won't Start
- Check battery connection and switch position
- Verify MicroPython installation
- Check for short circuits in wiring

### No Sensor Readings
- Run `test_scripts/i2c_test.py` to verify I2C bus
- Check sensor addresses and wiring
- Individual sensor tests in `test_scripts/`

### Display Issues
- Verify OLED address (0x3C) and I2C pins
- Check power connections (3.3V)
- Run `test_scripts/display_test.py`

### WiFi Problems
- Use "Reset WiFi" screen to clear settings
- Check credentials in access point mode
- Verify Pico W firmware supports WiFi

### Rotary Encoder Not Working
- Check pin connections (GP18/GP19/GP20)
- Verify pull-up resistors on button pin
- Run `test_scripts/encoder_display_test.py`

### Power Management Issues
- Adjust sleep times in `settings.json`
- Check APC1 SET/RST pin connections
- Verify battery voltage divider

## Project Structure

```
pico_portable_weather_station/
├── main.py                 # Main application with UI and power management
├── settings.json           # Runtime configuration (auto-generated)
├── boot.py                 # Boot configuration
├── lib/                    # Core libraries
│   ├── config.py           # Centralized configuration management
│   ├── screens.py          # Screen definitions and rendering
│   ├── display_utils.py    # OLED display utilities and font rendering
│   ├── font_renderer.py    # Unified font rendering system
│   ├── apc1.py             # APC1 air quality sensor driver
│   ├── apc1_power.py       # APC1 power control
│   ├── shtc3.py            # SHTC3 temp/humidity sensor driver
│   ├── battery.py          # Battery monitoring
│   ├── wifi_helper.py      # WiFi setup and configuration
│   ├── rotary.py           # Rotary encoder base library
│   ├── rotary_irq_rp2.py   # Pico-specific rotary encoder
│   ├── ssd1306.py          # SSD1306 OLED driver
│   ├── ezFBfont.py         # Advanced font rendering
│   ├── ezFBmarquee.py      # Text marquee/scroller
│   └── fonts/              # Font files (various sizes)
├── test_scripts/           # Individual component tests
└── README.md               # This file
```

## Development

### Adding New Sensors
1. Create driver in `lib/` following existing patterns
2. Add screen in `screens.py`
3. Update configuration in `config.py`
4. Add to main.py initialization

### Custom Fonts
- Place font files in `lib/fonts/`
- Use `get_font_module()` to load
- Supports ezFBfont format

### Testing
- Individual component tests in `test_scripts/`
- Run tests with `python test_script_name.py` on Pico

## License

This project is open source. See individual files for license information.

## Contributing

Contributions welcome! Please test on actual hardware before submitting PRs.
