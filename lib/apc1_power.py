# apc1_power.py
# Helper to manage APC1 sensor power control via SET and RESET pins.

from machine import Pin
import time


class APC1Power:
    """Encapsulates APC1 SET/RESET control pins.

    Wiring per README:
      - SET -> GP22 (pull low to sleep, high to enable)
      - RST -> GP21 (active low reset)
    """

    def __init__(self, set_pin=22, reset_pin=21):
        self.set = Pin(set_pin, Pin.OUT)
        self.reset = Pin(reset_pin, Pin.OUT)
        # Deassert reset and enable the device by default
        self.reset.value(1)
        self.set.value(1)
        self._enabled = True

    def enable(self):
        self.set.value(1)
        self._enabled = True

    def disable(self):
        self.set.value(0)
        self._enabled = False

    def is_enabled(self):
        # Reflect actual pin to be robust
        return self.set.value() == 1 and self._enabled

    def reset_pulse(self, pulse_ms=20):
        """Issue a short active-low reset pulse."""
        # Ensure device is enabled prior or after reset as needed
        self.reset.value(0)
        time.sleep_ms(pulse_ms)
        self.reset.value(1)
