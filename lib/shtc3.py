# shtc3.py
# Simple MicroPython driver for Sensirion SHTC3 temperature/humidity sensor
# Works with Raspberry Pi Pico or any MicroPython I2C host

import time

class SHTC3:
    DEFAULT_ADDR = 0x70

    def __init__(self, i2c, address=DEFAULT_ADDR):
        self.i2c = i2c
        self.addr = address
        self._wake()
        time.sleep_ms(1)

    # ---- Internal helpers ----
    def _write_cmd(self, cmd):
        """Send a 16-bit command to the sensor."""
        self.i2c.writeto(self.addr, bytes([(cmd >> 8) & 0xFF, cmd & 0xFF]))

    def _read_bytes(self, n):
        """Read n bytes from the sensor."""
        return self.i2c.readfrom(self.addr, n)

    # ---- Basic commands ----
    def _wake(self):
        self._write_cmd(0x3517)  # Wake up command
        time.sleep_ms(1)

    def _sleep(self):
        self._write_cmd(0xB098)  # Sleep command

    # ---- Measurement ----
    def measure(self):
        """
        Trigger a single measurement (no clock stretching, high precision).
        Returns tuple: (temperature_C, humidity_%RH)
        """
        # Wake up, measure, sleep again
        self._wake()
        self._write_cmd(0x7866)  # Measure T & RH, high precision, no clock stretching
        time.sleep_ms(15)

        data = self._read_bytes(6)
        self._sleep()

        # Unpack raw values (ignore CRC bytes)
        t_raw = (data[0] << 8) | data[1]
        rh_raw = (data[3] << 8) | data[4]

        # Convert using datasheet formulas
        temperature = -45 + (175 * t_raw / 65535.0)
        humidity = 100 * rh_raw / 65535.0
        return (temperature, humidity)

    # ---- Optional ----
    def reset(self):
        """Perform a soft reset."""
        self._write_cmd(0x805D)
        time.sleep_ms(2)
