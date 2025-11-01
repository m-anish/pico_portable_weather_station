from machine import Pin, I2C
import time
from ssd1306 import SSD1306_I2C
from rotary_irq_rp2 import RotaryIRQ

# ============================================================
# ===== SHTC3 Driver (Built-in, based on Sensirion datasheet)
# ============================================================
class SHTC3:
    DEFAULT_ADDR = 0x70

    def __init__(self, i2c, address=DEFAULT_ADDR):
        self.i2c = i2c
        self.addr = address
        self._wake()
        time.sleep_ms(1)

    def _write_cmd(self, cmd):
        self.i2c.writeto(self.addr, bytes([(cmd >> 8) & 0xFF, cmd & 0xFF]))

    def _read_bytes(self, n):
        return self.i2c.readfrom(self.addr, n)

    def _wake(self):
        self._write_cmd(0x3517)
        time.sleep_ms(1)

    def _sleep(self):
        self._write_cmd(0xB098)

    def reset(self):
        self._write_cmd(0x805D)
        time.sleep_ms(2)

    def measure(self):
        """Return (temperature_C, humidity_%RH)"""
        self._wake()
        self._write_cmd(0x7866)  # High precision, no clock stretching
        time.sleep_ms(15)
        data = self._read_bytes(6)
        self._sleep()

        t_raw = (data[0] << 8) | data[1]
        rh_raw = (data[3] << 8) | data[4]
        temperature = -45 + (175 * t_raw / 65535.0)
        humidity = 100 * rh_raw / 65535.0
        return (temperature, humidity)

# ============================================================
# ===== Main Program: Encoder + SHTC3 + OLED Display
# ============================================================

# ---- Hardware Configuration ----
I2C_SDA = 16   # GP16 (PIN21)
I2C_SCL = 17   # GP17 (PIN22)
ENC_A = 18     # GP18 (PIN24)
ENC_B = 19     # GP19 (PIN25)
ENC_SW = 20    # GP20 (PIN26)
OLED_ADDR = 0x3C
I2C_FREQ = 400000

# ---- Initialize I2C, OLED, and SHTC3 ----
i2c = I2C(0, sda=Pin(I2C_SDA), scl=Pin(I2C_SCL), freq=I2C_FREQ)
oled = SSD1306_I2C(128, 64, i2c, addr=OLED_ADDR)
sensor = SHTC3(i2c)

# ---- Initialize Encoder ----
encoder = RotaryIRQ(pin_num_clk=ENC_A,
                    pin_num_dt=ENC_B,
                    reverse=True,
                    range_mode=RotaryIRQ.RANGE_WRAP,
                    min_val=0,
                    max_val=1)
encoder.set(value=0)  # 0 = °C, 1 = °F

# ---- Button Setup ----
pin_sw = Pin(ENC_SW, Pin.IN, Pin.PULL_UP)
last_press_time = 0
PRESS_DEBOUNCE_MS = 200
unit_mode = 0  # 0=°C, 1=°F

def toggle_unit():
    global unit_mode
    unit_mode = 1 - unit_mode
    print("Unit changed to", "°F" if unit_mode else "°C")
    update_display(last_temp, last_humi)

def check_button():
    global last_press_time
    if not pin_sw.value():  # Active LOW
        now = time.ticks_ms()
        if time.ticks_diff(now, last_press_time) > PRESS_DEBOUNCE_MS:
            toggle_unit()
            last_press_time = now

# ---- OLED Display ----
def update_display(temp_c, humi):
    oled.fill(0)
    oled.text("SHTC3 Weather", 10, 0)
    if unit_mode == 0:
        oled.text(f"Temp: {temp_c:.1f} C", 10, 25)
    else:
        temp_f = temp_c * 1.8 + 32
        oled.text(f"Temp: {temp_f:.1f} F", 10, 25)
    oled.text(f"Humidity: {humi:.1f} %", 10, 45)
    oled.show()

# ---- Main Loop ----
last_temp, last_humi = 0.0, 0.0
update_display(last_temp, last_humi)

try:
    while True:
        # Measure
        temp_c, humi = sensor.measure()
        last_temp, last_humi = temp_c, humi
        print(f"Temperature: {temp_c:.2f} °C, Humidity: {humi:.2f} %RH")

        # Update OLED
        update_display(temp_c, humi)

        # 5-second refresh, but check button during wait
        for _ in range(50):
            check_button()
            time.sleep(0.1)

except KeyboardInterrupt:
    oled.fill(0)
    oled.text("Stopped", 40, 25)
    oled.show()
    print("Measurement stopped.")

