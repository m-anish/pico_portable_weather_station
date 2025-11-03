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
    
    def _crc8(self, data):
        """Calculate CRC-8 checksum (polynomial 0x31, init 0xFF).
        
        Args:
            data: bytes to calculate CRC for (should be 2 bytes)
        
        Returns:
            int: CRC-8 checksum value
        """
        crc = 0xFF
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x80:
                    crc = (crc << 1) ^ 0x31
                else:
                    crc = crc << 1
            crc &= 0xFF
        return crc

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
        Returns tuple: (temperature_C, humidity_%RH) or (None, None) on error
        """
        try:
            # Wake up, measure, sleep again
            self._wake()
            self._write_cmd(0x7866)  # Measure T & RH, high precision, no clock stretching
            time.sleep_ms(15)

            data = self._read_bytes(6)
            if len(data) != 6:
                print("SHTC3 error: Expected 6 bytes, got {}".format(len(data)))
                return (None, None)

            self._sleep()

            # Unpack raw values and CRC bytes
            t_raw = (data[0] << 8) | data[1]
            t_crc = data[2]
            rh_raw = (data[3] << 8) | data[4]
            rh_crc = data[5]
            
            # Verify CRC for temperature data
            t_crc_calc = self._crc8(bytes([data[0], data[1]]))
            if t_crc != t_crc_calc:
                print("SHTC3 error: Temperature CRC mismatch (got 0x{:02X}, expected 0x{:02X})".format(t_crc, t_crc_calc))
                return (None, None)
            
            # Verify CRC for humidity data
            rh_crc_calc = self._crc8(bytes([data[3], data[4]]))
            if rh_crc != rh_crc_calc:
                print("SHTC3 error: Humidity CRC mismatch (got 0x{:02X}, expected 0x{:02X})".format(rh_crc, rh_crc_calc))
                return (None, None)
            
            # Validate raw values (detect I2C bus errors)
            # 0xFFFF (65535) often indicates I2C communication error (bus returning all 1's)
            # 0x0000 is also suspicious for humidity
            if rh_raw == 0xFFFF or rh_raw == 0x0000:
                print("SHTC3 error: Invalid humidity raw value 0x{:04X}".format(rh_raw))
                return (None, None)
            
            # Temperature raw value sanity check (valid range per datasheet)
            # -40°C corresponds to raw ~2979, +125°C to raw ~61557
            # Allow some margin but reject clearly invalid values
            if t_raw < 2000 or t_raw > 62000:
                print("SHTC3 warning: Suspicious temperature raw value {}".format(t_raw))
                # Don't return here, as extreme temps might be valid in some cases
            
            # Convert using datasheet formulas
            temperature = -45 + (175 * t_raw / 65535.0)
            humidity = 100 * rh_raw / 65535.0
            
            # Final sanity checks on converted values
            # Temperature: datasheet specifies -40°C to +125°C operating range
            if temperature < -50 or temperature > 130:
                print("SHTC3 error: Temperature out of range: {:.1f}°C".format(temperature))
                return (None, None)
            
            # Humidity: must be 0-100%
            if humidity < 0 or humidity > 100:
                print("SHTC3 error: Humidity out of range: {:.1f}%".format(humidity))
                return (None, None)
            
            return (temperature, humidity)
        except Exception as e:
            # Return None values on any error to allow graceful degradation
            print("SHTC3 error: {}".format(e))
            return (None, None)

    # ---- Optional ----
    def reset(self):
        """Perform a soft reset."""
        self._write_cmd(0x805D)
        time.sleep_ms(2)
