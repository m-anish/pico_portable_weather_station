# apc1.py
# MicroPython driver for Sciosense APC1 Weather/Air Quality Sensor
# by Anish M. (based on APC1 reference implementation)
#
# Usage:
#   from machine import I2C, Pin
#   from apc1 import APC1
#
#   i2c = I2C(0, sda=Pin(16), scl=Pin(17))
#   sensor = APC1(i2c)
#   print(sensor.read_all())

import time

class APC1:
    """Driver for Sciosense APC1 Weather and Air Quality Sensor (I2C version)."""

    DEFAULT_I2C_ADDR = 0x12

    _REG_MAP = [
        ('PM1.0',  0x04, 2, 1,    'µg/m³', 'PM1.0 Mass Concentration'),
        ('PM2.5',  0x06, 2, 1,    'µg/m³', 'PM2.5 Mass Concentration'),
        ('PM10',   0x08, 2, 1,    'µg/m³', 'PM10 Mass Concentration'),
        ('TVOC',   0x1C, 2, 1,    'ppb',   'Total Volatile Organic Compounds'),
        ('eCO2',   0x1E, 2, 1,    'ppm',   'Equivalent CO₂ concentration'),
        ('T-comp', 0x22, 2, 0.1,  '°C',    'Compensated Temperature'),
        ('RH-comp',0x24, 2, 0.1,  '%',     'Compensated Relative Humidity'),
        ('T-raw',  0x26, 2, 0.1,  '°C',    'Raw Temperature'),
        ('RH-raw', 0x28, 2, 0.1,  '%',     'Raw Relative Humidity'),
        ('AQI',    0x3A, 1, 1,    '',      'AQI according to TVOC')
    ]

    def __init__(self, i2c, address=DEFAULT_I2C_ADDR):
        """
        Initialize APC1 with an existing I2C object.

        :param i2c: machine.I2C instance
        :param address: I2C address of APC1 (default 0x12)
        """
        self.i2c = i2c
        self.address = address

    # ----------------------------
    #   Low-level register access
    # ----------------------------
    def _read_reg(self, reg, length):
        """Read raw bytes from APC1 register."""
        return self.i2c.readfrom_mem(self.address, reg, length)

    # ----------------------------
    #   High-level API
    # ----------------------------
    def read(self, name):
        """
        Read a single parameter by name, e.g. 'PM2.5' or 'T-comp'.

        :return: dict with {value, unit, description}
        """
        reg_entry = next((r for r in self._REG_MAP if r[0] == name), None)
        if reg_entry is None:
            raise ValueError("Unknown register name: " + name)

        reg, length, scale, unit, desc = reg_entry[1], reg_entry[2], reg_entry[3], reg_entry[4], reg_entry[5]
        data = self._read_reg(reg, length)
        if len(data) != length:
            raise RuntimeError("I2C read error")

        raw_val = int.from_bytes(data, "big")
        val = raw_val * scale
        return {"value": val, "unit": unit, "description": desc}

    def read_all(self):
        """Return a dictionary of all available sensor readings."""
        results = {}
        for name, reg, length, scale, unit, desc in self._REG_MAP:
            try:
                data = self._read_reg(reg, length)
                raw_val = int.from_bytes(data, "big")
                val = raw_val * scale
                results[name] = {"value": val, "unit": unit, "description": desc}
            except OSError:
                results[name] = {"value": None, "unit": unit, "description": desc}
        return results

    @staticmethod
    def compute_aqi_pm25(pm25):
        """Compute AQI value from PM2.5 concentration (µg/m³) using EPA breakpoints.

        Returns an integer in the 0-500 range. If pm25 is None, returns None.
        """
        if pm25 is None:
            return None
        # Breakpoint-based linear interpolation
        if pm25 <= 12:
            return 50 * pm25 / 12
        if pm25 <= 35.4:
            return 50 + (pm25 - 12.1) * (100 - 51) / (35.4 - 12.1)
        if pm25 <= 55.4:
            return 101 + (pm25 - 35.5) * (150 - 101) / (55.4 - 35.5)
        if pm25 <= 150.4:
            return 151 + (pm25 - 55.5) * (200 - 151) / (150.4 - 55.5)
        if pm25 <= 250.4:
            return 201 + (pm25 - 150.5) * (300 - 201) / (250.4 - 150.5)
        if pm25 <= 350.4:
            return 301 + (pm25 - 250.5) * (400 - 301) / (350.4 - 250.5)
        if pm25 <= 500.4:
            return 401 + (pm25 - 350.5) * (500 - 401) / (500.4 - 350.5)
        return 500
