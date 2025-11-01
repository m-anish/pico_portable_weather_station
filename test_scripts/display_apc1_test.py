from machine import Pin, I2C
import time
from ssd1306 import SSD1306_I2C
from apc1 import APC1

# ===== Hardware configuration =====
I2C_SDA = 16   # GP16 (PIN21)
I2C_SCL = 17   # GP17 (PIN22)
I2C_FREQ = 400000
OLED_ADDR = 0x3C
APC1_ADDR = 0x12

# ===== Initialize I2C bus =====
i2c = I2C(0, sda=Pin(I2C_SDA), scl=Pin(I2C_SCL), freq=I2C_FREQ)

# ===== Initialize OLED =====
oled = SSD1306_I2C(128, 64, i2c, addr=OLED_ADDR)

# ===== Initialize APC1 sensor =====
sensor = APC1(i2c, address=APC1_ADDR)

# ===== Display helper =====
def update_display(pm1, pm25, pm10):
    """Update OLED with PM readings."""
    oled.fill(0)
    oled.text("Sciosense APC1", 10, 0)
    oled.text(f"PM1.0 : {pm1:.1f} ug/m3", 5, 20)
    oled.text(f"PM2.5 : {pm25:.1f} ug/m3", 5, 35)
    oled.text(f"PM10  : {pm10:.1f} ug/m3", 5, 50)
    oled.show()

# ===== Main loop =====
try:
    while True:
        try:
            data = sensor.read_all()
            pm1 = data.get('PM1.0', {}).get('value', 0)
            pm25 = data.get('PM2.5', {}).get('value', 0)
            pm10 = data.get('PM10', {}).get('value', 0)

            print(f"PM1.0={pm1:.1f}  PM2.5={pm25:.1f}  PM10={pm10:.1f}")
            update_display(pm1, pm25, pm10)

        except Exception as e:
            print("Sensor read error:", e)
            oled.fill(0)
            oled.text("Sensor Error", 20, 25)
            oled.show()

        time.sleep(5)  # Refresh every 5 seconds

except KeyboardInterrupt:
    oled.fill(0)
    oled.text("Stopped", 40, 25)
    oled.show()
    print("Display stopped.")
