# Pico Portable Weather Sensor

A portable weather sensor project for Raspberry Pi Pico with MicroPython, designed to measure and log environmental data.

## Getting Started

1. Copy the `main.py` file to your Raspberry Pi Pico
2. The LED on pin 25 will start blinking

## Requirements

- Raspberry Pi Pico
- MicroPython firmware
- Thonny IDE or any other MicroPython-compatible IDE

## Hardware Details
 
 - I2C Pins:
    - SDA: PIN21 -- GP16 -- SDA0
    - SCL: PIN22 -- GP17 -- SCL0
 - EC11 Rotary Encoder:
    - A: PIN24 -- GP18
    - B: PIN25 -- GP19
    - C: PIN26 -- GP20
 - I2C Modules connected:
    - SHTC3
    - Sciosense APC1 Combined Weather Sensor (I2C Version)
      - SET Pin -- PIN29 -- GP22 -- Pull low for Deep Sleep. Up for Active mode.
      - RST Pin -- PIN27 -- GP21 -- Pull low to Reset Device. Up for Active mode.
    - 0.96in I2C OLED Display
 - Li-Ion Battery:
    - TP4056 module connected via global ON/OFF Switch
    - Protected battery output positive terminal connected to VSYS Pin
    - Voltage divider `0.5 x Battery voltage` connected to GP26-ADC0 Pin for analog sensing
 - Pico MicroUSB port not normally exposed except when in development mode. During that, keep battery switch in OFF position. 

## Project Structure

- `main.py`: Main application code with LED blink example
