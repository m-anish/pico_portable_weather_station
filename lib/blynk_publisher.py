"""blynk_publisher.py
Robust Blynk MQTT publisher that reads from sensor cache.

Publishes sensor data to Blynk cloud with graceful error handling.
Never crashes the main loop - all exceptions are caught and logged.
"""

import time
try:
    import uasyncio as asyncio
except ImportError:
    import asyncio


class BlynkPublisher:
    """Publishes sensor cache data to Blynk with robust error handling.
    
    Features:
    - Reads from sensor_cache (decoupled from sensors)
    - Graceful error handling (never crashes)
    - Runtime enable/disable support
    - Connection state tracking
    """
    
    def __init__(self, sensor_cache, blynk_mqtt, update_interval_s=30):
        """Initialize Blynk publisher.
        
        Args:
            sensor_cache: SensorCache instance to read from
            blynk_mqtt: blynk_mqtt module instance
            update_interval_s: How often to publish data (default: 30s)
        """
        self.cache = sensor_cache
        self.mqtt = blynk_mqtt.mqtt
        self.update_interval_s = update_interval_s
        self.enabled = False
        self.mqtt_connected = False
        self.last_publish = 0
        self.publish_count = 0
        self.error_count = 0
        
        # Track connection state via callbacks
        self._setup_callbacks(blynk_mqtt)
    
    def _setup_callbacks(self, blynk_mqtt):
        """Setup MQTT connection callbacks."""
        # Save original callbacks
        original_connected = blynk_mqtt.on_connected
        original_disconnected = blynk_mqtt.on_disconnected
        
        # Wrap callbacks to track state
        def on_connected_wrapper():
            self.mqtt_connected = True
            print("✓ Blynk MQTT connected")
            # Call original callback
            if original_connected and original_connected != blynk_mqtt._dummy:
                try:
                    original_connected()
                except Exception as e:
                    print(f"Blynk connected callback error: {e}")
        
        def on_disconnected_wrapper():
            self.mqtt_connected = False
            print("✗ Blynk MQTT disconnected")
            # Call original callback
            if original_disconnected and original_disconnected != blynk_mqtt._dummy:
                try:
                    original_disconnected()
                except Exception as e:
                    print(f"Blynk disconnected callback error: {e}")
        
        # Set wrapped callbacks
        blynk_mqtt.on_connected = on_connected_wrapper
        blynk_mqtt.on_disconnected = on_disconnected_wrapper
    
    def enable(self):
        """Enable MQTT publishing."""
        self.enabled = True
        print("Blynk publisher enabled")
    
    def disable(self):
        """Disable MQTT publishing."""
        self.enabled = False
        print("Blynk publisher disabled")
    
    def is_ready(self):
        """Check if publisher is ready to publish."""
        return self.enabled and self.mqtt_connected
    
    def _publish_value(self, datastream, value):
        """Publish a single value to Blynk datastream.
        
        Args:
            datastream: Datastream name (e.g., "Temperature")
            value: Value to publish (or None to skip)
        
        Returns:
            bool: True if published successfully, False otherwise
        """
        if value is None:
            return False
        
        try:
            topic = f"ds/{datastream}"
            self.mqtt.publish(topic, value)
            return True
        except Exception as e:
            print(f"Publish error ({datastream}): {e}")
            self.error_count += 1
            return False
    
    def _publish_all_sensors(self):
        """Publish all sensor data from cache to Blynk.
        
        Reads from sensor_cache and publishes to Blynk datastreams:
        - Temperature (from SHTC3)
        - Humidity (from SHTC3)
        - PM1 (from APC1)
        - PM2_5 (from APC1)
        - TVOC (from APC1)
        - eCO2 (from APC1)
        - AQI (computed from PM2.5)
        """
        published = []
        
        # Get SHTC3 data
        temp, humidity, _ = self.cache.get_shtc3()
        if self._publish_value("Temperature", temp):
            published.append("Temperature")
        if self._publish_value("Humidity", humidity):
            published.append("Humidity")
        
        # Get APC1 data
        apc1_data = self.cache.get_apc1_all()
        if self._publish_value("PM1", apc1_data.get('pm1')):
            published.append("PM1")
        if self._publish_value("PM2_5", apc1_data.get('pm25')):
            published.append("PM2_5")
        if self._publish_value("TVOC", apc1_data.get('tvoc')):
            published.append("TVOC")
        if self._publish_value("eCO2", apc1_data.get('eco2')):
            published.append("eCO2")
        if self._publish_value("AQI", apc1_data.get('aqi_pm25')):
            published.append("AQI")
        
        return published
    
    async def publish_task(self):
        """Async task to periodically publish sensor data to Blynk.
        
        This task runs forever and publishes data at the configured interval.
        All exceptions are caught and logged - never crashes the main loop.
        """
        print(f"Blynk publisher task started (interval: {self.update_interval_s}s)")
        
        while True:
            try:
                # Wait for the publish interval
                await asyncio.sleep(self.update_interval_s)
                
                # Check if we should publish
                if not self.is_ready():
                    continue
                
                # Publish all sensor data
                published = self._publish_all_sensors()
                
                # Update stats
                if published:
                    self.last_publish = time.time()
                    self.publish_count += 1
                    print(f"📤 Blynk: Published {len(published)} datastreams")
                
            except Exception as e:
                # Catch ALL exceptions - never crash
                print(f"Blynk publish task error: {e}")
                self.error_count += 1
                # Continue running
    
    def get_stats(self):
        """Get publisher statistics.
        
        Returns:
            dict: Statistics including publish count, errors, etc.
        """
        return {
            'enabled': self.enabled,
            'connected': self.mqtt_connected,
            'publish_count': self.publish_count,
            'error_count': self.error_count,
            'last_publish': self.last_publish,
            'interval_s': self.update_interval_s
        }
