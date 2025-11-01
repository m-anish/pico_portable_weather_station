from machine import Pin, I2C
import time
from ssd1306 import SSD1306_I2C
from rotary_irq_rp2 import RotaryIRQ  # For Raspberry Pi Pico (RP2040)

# ===== OLED / I2C Configuration =====
I2C_SDA = 16   # GP16 (PIN21)
I2C_SCL = 17   # GP17 (PIN22)
I2C_FREQ = 400000
OLED_WIDTH = 128
OLED_HEIGHT = 64
OLED_ADDR = 0x3C

# ===== Encoder Pin Configuration =====
ENC_A = 18    # GP18 (PIN24)
ENC_B = 19    # GP19 (PIN25)
ENC_SW = 20   # GP20 (PIN26)

# ===== Initialize OLED =====
i2c = I2C(0, sda=Pin(I2C_SDA), scl=Pin(I2C_SCL), freq=I2C_FREQ)
oled = SSD1306_I2C(OLED_WIDTH, OLED_HEIGHT, i2c, addr=OLED_ADDR)

def update_display(value, message=""):
    """Show current encoder value and message."""
    oled.fill(0)
    oled.text("Encoder Display Test", 0, 0)
    oled.text(f"Value: {value}", 10, 25)
    if message:
        oled.text(message, 10, 50)
    oled.show()

# ===== Rotary Encoder Setup =====
r = RotaryIRQ(
    pin_num_clk=ENC_A,
    pin_num_dt=ENC_B,
    min_val=-999,
    max_val=999,
    reverse=True,   # Fix direction (CW/CCW swapped otherwise)
    range_mode=RotaryIRQ.RANGE_UNBOUNDED
)

r.set(value=0)  # Start from 0

# ===== Button Setup =====
pin_sw = Pin(ENC_SW, Pin.IN, Pin.PULL_UP)
last_press_time = 0
PRESS_DEBOUNCE_MS = 150

def check_button():
    """Detect short button presses with debounce."""
    global last_press_time
    if not pin_sw.value():  # Active LOW
        now = time.ticks_ms()
        if time.ticks_diff(now, last_press_time) > PRESS_DEBOUNCE_MS:
            update_display(r.value(), "Button pressed!")
            print("Button pressed!")
            last_press_time = now

# ===== Main Loop =====
last_val = r.value()
update_display(last_val, "Rotate or Press")

try:
    while True:
        val_new = r.value()
        if val_new != last_val:
            if val_new > last_val:
                update_display(val_new, "CW")
                print("CW →", val_new)
            else:
                update_display(val_new, "CCW")
                print("CCW →", val_new)
            last_val = val_new

        check_button()
        time.sleep(0.02)

except KeyboardInterrupt:
    oled.fill(0)
    oled.text("Test Ended", 25, 25)
    oled.show()
    print("Encoder display test stopped.")
