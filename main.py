# Basic Skeleton for Raspberry Pi Pico MicroPython Project

# Import necessary libraries
import machine
import time

# Initialize an LED on pin 25
led = machine.Pin(25, machine.Pin.OUT)

# Main loop
while True:
    led.on()  # Turn on the LED
    time.sleep(1)  # Wait for 1 second
    led.off()  # Turn off the LED
    time.sleep(1)  # Wait for 1 second
