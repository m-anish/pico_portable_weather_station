#!/usr/bin/env python3
"""
Test script to verify AP mode fixes for CYW43 timeout issue.
This script tests the improved start_config_ap function.
"""

import sys
import os

# Add the lib directory to the path so we can import modules
sys.path.append('lib')

try:
    import machine
    from machine import Pin, I2C
    from ssd1306 import SSD1306_I2C
    import wifi_helper
    from wifi_config import reset_wifi
    import logger
    
    print("=== AP Mode Fix Test ===")
    
    # Initialize OLED for testing (optional)
    try:
        sda = 16
        scl = 17
        i2c = I2C(0, sda=Pin(sda), scl=Pin(scl), freq=400000)
        oled = SSD1306_I2C(128, 64, i2c, addr=0x3C)
        oled.fill(0)
        oled.text("AP Test", 0, 0)
        oled.show()
        print("✓ OLED initialized")
    except Exception as e:
        print(f"⚠ OLED init failed: {e}")
        oled = None
    
    # Reset WiFi config to trigger AP mode
    print("Resetting WiFi config to trigger AP mode...")
    if reset_wifi():
        print("✓ WiFi config reset")
    else:
        print("⚠ WiFi config reset failed")
    
    # Test the improved AP function
    print("Testing improved AP setup...")
    
    def test_save_callback(ssid, password):
        print(f"WiFi credentials received: SSID={ssid}, Password={'*' * len(password)}")
    
    try:
        # This should now work without CYW43 timeout errors
        wifi_helper.start_config_ap(
            ap_ssid="PICO_TEST",
            ap_password="12345678",
            on_save=test_save_callback,
            oled=oled
        )
    except Exception as e:
        print(f"✗ AP setup failed: {e}")
        if oled:
            oled.fill(0)
            oled.text("AP Test Failed", 0, 0)
            oled.text(str(e)[:16], 0, 16)
            oled.show()
        sys.exit(1)
    
    print("✓ AP setup completed successfully")
    
except ImportError as e:
    print(f"Import error (expected on non-Pico environment): {e}")
    print("This test is designed to run on a Raspberry Pi Pico W")
    
except Exception as e:
    print(f"Test failed: {e}")
    sys.exit(1)
