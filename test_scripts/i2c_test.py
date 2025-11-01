from machine import Pin, I2C
import time

# Map of known I2C addresses to device names
DEVICE_NAMES = {
    0x12: "Sciosence APC1 (Weather Sensor)",
    0x3C: "OLED Display",
    0x70: "SHTC3 Temperature/Humidity Sensor",
}

def scan_i2c():
    # Configure APC1 control pins
    apc1_set = Pin(22, Pin.OUT, value=1)  # Set high for active mode
    apc1_rst = Pin(21, Pin.OUT, value=1)  # Set high to take out of reset
    
    # Initialize I2C with specified pins
    i2c = I2C(0, sda=Pin(16), scl=Pin(17), freq=400000)  # 400kHz I2C
    
    print("Scanning I2C bus...")
    devices = i2c.scan()
    
    if len(devices) == 0:
        print("No I2C devices found!")
    else:
        print("I2C devices found:")
        for device in devices:
            name = DEVICE_NAMES.get(device, "Unknown device")
            print(f"- Address: 0x{device:02X} ({device}) → {name}")
    
    return devices

if __name__ == "__main__":
    print("Starting I2C scan...")
    devices = scan_i2c()
    print("Scan complete.")
    
    # Keep the program running to maintain power to APC1
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nTest completed.")
