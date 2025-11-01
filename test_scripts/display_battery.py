from machine import Pin, ADC, I2C
import time
from ssd1306 import SSD1306_I2C

# ===== Hardware configuration =====
I2C_SDA = 16   # GP16 (PIN21)
I2C_SCL = 17   # GP17 (PIN22)
I2C_FREQ = 400000
OLED_ADDR = 0x3C
BAT_ADC_PIN = 26   # GP26-ADC0, 0.5x battery voltage divider

# ===== Initialize I2C & OLED =====
i2c = I2C(0, sda=Pin(I2C_SDA), scl=Pin(I2C_SCL), freq=I2C_FREQ)
oled = SSD1306_I2C(128, 64, i2c, addr=OLED_ADDR)

# ===== Initialize ADC for battery sense =====
adc = ADC(BAT_ADC_PIN)

# ===== Helper functions =====
def read_battery_voltage():
    """Read battery voltage (with 0.5 divider)."""
    raw = adc.read_u16()        # 0–65535
    v_in = raw * 3.3 / 65535.0  # ADC reference = 3.3 V
    v_batt = v_in * 2           # Compensate divider (0.5×)
    return v_batt

def battery_percentage(v):
    """Approximate Li-ion battery percentage based on voltage."""
    if v < 3.0:
        return 0
    elif v > 4.2:
        return 100
    else:
        # Rough linear approximation between 3.0 V and 4.2 V
        return int((v - 3.0) / (4.2 - 3.0) * 100)

def update_display(v_batt, percent):
    oled.fill(0)
    oled.text("Battery Monitor", 8, 0)
    oled.text(f"Voltage: {v_batt:.2f} V", 10, 25)
    oled.text(f"Charge : {percent:3d} %", 10, 45)
    oled.show()

# ===== Main loop =====
try:
    while True:
        v_batt = read_battery_voltage()
        percent = battery_percentage(v_batt)

        print(f"Battery: {v_batt:.2f} V  ({percent}%)")
        update_display(v_batt, percent)

        time.sleep(5)  # refresh every 5 seconds

except KeyboardInterrupt:
    oled.fill(0)
    oled.text("Stopped", 40, 25)
    oled.show()
    print("Display stopped.")

