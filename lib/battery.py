# battery.py
# Simple MicroPython battery sensing helper/driver
# Supports ADC-based Li-ion battery voltage & % estimation.
#
# Example:
#   from machine import ADC, Pin
#   from battery import Battery
#
#   batt = Battery(adc_pin=26, divider_ratio=2.0)
#   v, p = batt.read()
#   print("Battery:", v, "V", p, "%")

from machine import ADC, Pin

class Battery:
    def __init__(self, adc_pin=26, divider_ratio=2.0, vref=3.3,
                 v_empty=3.0, v_full=4.2, charge_pin=None):
        """
        :param adc_pin: ADC pin number connected to the battery divider
        :param divider_ratio: Ratio of (battery voltage / ADC input voltage)
                              e.g. 2.0 means input is 0.5× battery voltage
        :param vref: Reference voltage for ADC conversion (typically 3.3 V)
        :param v_empty: Voltage representing 0% charge
        :param v_full: Voltage representing 100% charge
        :param charge_pin: Optional GPIO pin for charge detect (active LOW)
        """
        self.adc = ADC(adc_pin)
        self.divider_ratio = divider_ratio
        self.vref = vref
        self.v_empty = v_empty
        self.v_full = v_full
        self.charge_pin = Pin(charge_pin, Pin.IN, Pin.PULL_UP) if charge_pin is not None else None

    def read_voltage(self):
        """Return measured battery voltage in volts, or None on error."""
        try:
            raw = self.adc.read_u16()           # 0–65535
            v_adc = raw * self.vref / 65535.0   # Convert to ADC input voltage
            v_batt = v_adc * self.divider_ratio # Compensate divider
            return v_batt
        except Exception as e:
            return None

    def read_percentage(self):
        """Estimate battery percentage (simple linear model), or None on error."""
        try:
            v = self.read_voltage()
            if v is None:
                return None
            if v <= self.v_empty:
                return 0
            elif v >= self.v_full:
                return 100
            else:
                return int((v - self.v_empty) / (self.v_full - self.v_empty) * 100)
        except Exception as e:
            return None

    def is_charging(self):
        """
        Optional: return True if charge_pin indicates charging.
        Returns None if no charge_pin configured.
        """
        if self.charge_pin is None:
            return None
        return self.charge_pin.value() == 0  # Active LOW

    def read(self):
        """Return tuple: (voltage, percentage, state)"""
        v = self.read_voltage()
        p = self.read_percentage()
        state = None
        if self.charge_pin is not None:
            state = "charging" if self.is_charging() else "discharging"
        return (v, p, state)
