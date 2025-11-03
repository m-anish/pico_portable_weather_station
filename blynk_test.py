# blynk_test.py
# Test script to publish dummy sensor values to Blynk
# Tests datastreams: Temperature, Humidity, PM2_5

import sys, time, asyncio, random
if sys.platform == "linux": sys.path.append("lib")

from config import load_settings, get_blynk_settings
import blynk_mqtt

# Test configuration
FIRMWARE_VERSION = "0.1.0-test"
PUBLISH_INTERVAL_MS = 5000  # 5 seconds for testing (faster than production)

# Blynk MQTT instance
mqtt = blynk_mqtt.mqtt

# Dummy sensor data generators
def get_dummy_temperature():
    """Generate dummy temperature value (20-30°C)"""
    return round(20 + random.uniform(0, 10), 1)

def get_dummy_humidity():
    """Generate dummy humidity value (40-70%)"""
    return round(40 + random.uniform(0, 30), 1)

def get_dummy_pm25():
    """Generate dummy PM2.5 value (0-100 µg/m³)"""
    return round(random.uniform(0, 100), 0)

# Async publisher task
async def publisher_task():
    """Publish dummy sensor values to Blynk every 5 seconds"""
    print("Publisher task started")
    
    while True:
        try:
            # Generate dummy values
            temp = get_dummy_temperature()
            humidity = get_dummy_humidity()
            pm25 = get_dummy_pm25()
            
            # Publish to Blynk datastreams (using datastream names)
            mqtt.publish("ds/Temperature", temp)
            mqtt.publish("ds/Humidity", humidity)
            mqtt.publish("ds/PM2_5", pm25)
            
            print(f"Published: Temp={temp}°C, Humidity={humidity}%, PM2.5={pm25}µg/m³")
            
        except Exception as e:
            print(f"Publisher error: {e}")
        
        await asyncio.sleep_ms(PUBLISH_INTERVAL_MS)

# MQTT event callbacks
def mqtt_connected():
    """Called when MQTT connection is established"""
    print("✓ MQTT connected to Blynk")
    print("Publishing dummy sensor data...")
    print("  Temperature = 20-30°C")
    print("  Humidity = 40-70%")
    print("  PM2_5 = 0-100 µg/m³")

def mqtt_disconnected():
    """Called when MQTT connection is lost"""
    print("✗ MQTT disconnected")

def mqtt_callback(topic, payload):
    """Handle incoming MQTT messages"""
    print(f"Received: {topic} = {payload}")

# WiFi connection
def connect_wifi(ssid, password):
    """Connect to WiFi network"""
    import network
    
    sta = network.WLAN(network.STA_IF)
    if not sta.isconnected():
        print(f"Connecting to WiFi '{ssid}'...", end="")
        sta.active(True)
        sta.disconnect()
        sta.connect(ssid, password)
        
        timeout = 30  # 30 second timeout
        start = time.time()
        
        while not sta.isconnected():
            if time.time() - start > timeout:
                raise Exception("WiFi connection timeout")
            
            time.sleep(1)
            print(".", end="")
            
            if sta.status() == network.STAT_NO_AP_FOUND:
                raise Exception("WiFi Access Point not found")
            elif sta.status() == network.STAT_WRONG_PASSWORD:
                raise Exception("Wrong WiFi credentials")
        
        print(" ✓")
        print(f"IP Address: {sta.ifconfig()[0]}")
        return sta
    else:
        print(f"Already connected to WiFi: {sta.ifconfig()[0]}")
        return sta

# Main setup and loop
def main():
    """Main entry point"""
    print("=" * 50)
    print("Blynk Test Script - Dummy Sensor Publishing")
    print("=" * 50)
    
    # Load settings
    print("\n1. Loading configuration...")
    settings = load_settings()
    blynk_cfg = get_blynk_settings(settings)
    wifi_cfg = settings.get("wifi", {})
    
    # Validate Blynk configuration
    if not blynk_cfg["enabled"]:
        print("✗ Blynk is disabled in settings.json")
        print("  Set 'blynk.enabled' to true and configure credentials")
        return
    
    if not blynk_cfg["auth_token"]:
        print("✗ Blynk auth_token not configured")
        print("  Add your Blynk auth token to settings.json")
        return
    
    print(f"  Template ID: {blynk_cfg['template_id']}")
    print(f"  Template Name: {blynk_cfg['template_name']}")
    print(f"  MQTT Broker: {blynk_cfg['mqtt_broker']}")
    
    # Validate WiFi configuration
    if not wifi_cfg.get("ssid"):
        print("✗ WiFi SSID not configured in settings.json")
        return
    
    # Setup Blynk MQTT
    print("\n2. Configuring Blynk MQTT...")
    blynk_mqtt.on_connected = mqtt_connected
    blynk_mqtt.on_disconnected = mqtt_disconnected
    blynk_mqtt.on_message = mqtt_callback
    blynk_mqtt.firmware_version = FIRMWARE_VERSION
    
    # Connect WiFi
    if sys.platform != "linux":
        print("\n3. Connecting to WiFi...")
        try:
            connect_wifi(wifi_cfg["ssid"], wifi_cfg.get("password", ""))
        except Exception as e:
            print(f"✗ WiFi connection failed: {e}")
            return
    else:
        print("\n3. Skipping WiFi (running on Linux)")
    
    # Start async tasks
    print("\n4. Starting Blynk publisher...")
    print("=" * 50)
    print("Press Ctrl+C to stop\n")
    
    try:
        asyncio.run(asyncio.gather(
            blynk_mqtt.task(),
            publisher_task()
        ))
    except KeyboardInterrupt:
        print("\n\n✓ Test stopped by user")
    except Exception as e:
        print(f"\n✗ Error: {e}")
    finally:
        # Clean up
        asyncio.new_event_loop()
        print("=" * 50)

if __name__ == "__main__":
    main()
