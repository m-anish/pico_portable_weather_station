# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2025-03-11

### Added
- Runtime-configurable screen timeout with UI controls
- Debug menu with exit program option in settings
- Improved debug mode with infinite loop for easier interruption

### Fixed
- JSON formatting bug causing errors
- Screen flash on initial boot
- Changed sys.exit() to KeyboardInterrupt exception for better compatibility

### Changed
- Removed settings.json from git repository
- Added *.json to .gitignore

## [1.0.0] - Previous Release

Initial stable release with core functionality:
- Multi-sensor support (APC1 air quality + SHTC3 temp/humidity)
- EPA-standard AQI calculations
- Interactive OLED display with rotary encoder
- Power management with configurable sleep modes
- Battery monitoring with Li-Ion estimation
- WiFi configuration via access point
- Multiple display screens for all sensor data

[1.1.0]: https://github.com/m-anish/pico_portable_weather_station/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/m-anish/pico_portable_weather_station/releases/tag/v1.0.0
