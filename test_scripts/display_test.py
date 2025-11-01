from machine import Pin, I2C
import time
from ssd1306 import SSD1306_I2C

# I2C configuration (adjust SDA/SCL pins if needed)
I2C_SDA = 16
I2C_SCL = 17
I2C_FREQ = 400000
OLED_WIDTH = 128
OLED_HEIGHT = 64
OLED_ADDR = 0x3C

def init_display():
    i2c = I2C(0, sda=Pin(I2C_SDA), scl=Pin(I2C_SCL), freq=I2C_FREQ)
    print("I2C devices found:", [hex(addr) for addr in i2c.scan()])
    display = SSD1306_I2C(OLED_WIDTH, OLED_HEIGHT, i2c, addr=OLED_ADDR)
    display.fill(0)
    display.show()
    return display

def display_test_sequence(display):
    # 1. Show startup message
    display.text("Display Test", 10, 10)
    display.text("Starting...", 20, 30)
    display.show()
    time.sleep(2)

    # 2. Draw horizontal and vertical lines
    display.fill(0)
    for y in range(0, OLED_HEIGHT, 8):
        display.line(0, y, OLED_WIDTH - 1, y, 1)
    for x in range(0, OLED_WIDTH, 8):
        display.line(x, 0, x, OLED_HEIGHT - 1, 1)
    display.show()
    time.sleep(2)

    # 3. Show text in different positions
    display.fill(0)
    display.text("Hello!", 0, 0)
    display.text("MicroPython", 0, 16)
    display.text("Raspberry Pi", 0, 32)
    display.text("Pico OLED", 0, 48)
    display.show()
    time.sleep(2)

    # 4. Scroll text horizontally
    for offset in range(OLED_WIDTH):
        display.fill(0)
        display.text("Scrolling Text >", -offset, 30)
        display.show()
        time.sleep(0.02)

    # 5. Invert display
    display.invert(1)
    time.sleep(1)
    display.invert(0)
    time.sleep(1)

    # 6. Done
    display.fill(0)
    display.text("Test Complete", 15, 25)
    display.show()
    print("Display test complete.")

def main():
    display = init_display()
    display_test_sequence(display)

if __name__ == "__main__":
    main()

