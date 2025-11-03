"""sensor_cache.py
Thread-safe sensor data cache with timestamps for async architecture.

Provides centralized storage for sensor readings, allowing display updates
to be independent of sensor I2C operations.
"""

import time


class SensorCache:
    """Thread-safe cache for sensor readings with timestamps.
    
    Stores latest readings from all sensors and provides thread-safe
    access methods. Pre-allocates data structures to minimize memory
    allocation during runtime.
    """
    
    def __init__(self):
        """Initialize sensor cache with pre-allocated buffers."""
        # Pre-allocate sensor data dictionary
        self._data = {
            # SHTC3 readings
            'temperature': None,
            'humidity': None,
            'temp_timestamp': 0,
            
            # APC1 readings
            'pm1': None,
            'pm25': None,
            'pm10': None,
            'tvoc': None,
            'eco2': None,
            'aqi_tvoc': None,
            'temp_comp': None,
            'rh_comp': None,
            'pm_timestamp': 0,
            
            # Battery readings
            'battery_voltage': None,
            'battery_percent': None,
            'battery_timestamp': 0,
            
            # Computed values
            'aqi_pm25': None,
        }
        
        # Lock flag for thread safety (simple busy-wait lock)
        self._lock = False
    
    def _acquire_lock(self):
        """Simple spin-lock acquisition."""
        while self._lock:
            pass  # Busy wait
        self._lock = True
    
    def _release_lock(self):
        """Release the lock."""
        self._lock = False
    
    # -------- SHTC3 Methods --------
    def update_shtc3(self, temperature, humidity):
        """Update SHTC3 temperature and humidity readings.
        
        Args:
            temperature: Temperature in Celsius (or None on error)
            humidity: Relative humidity percentage (or None on error)
        """
        self._acquire_lock()
        try:
            self._data['temperature'] = temperature
            self._data['humidity'] = humidity
            self._data['temp_timestamp'] = time.time()
        finally:
            self._release_lock()
    
    def get_shtc3(self):
        """Get SHTC3 readings.
        
        Returns:
            tuple: (temperature, humidity, timestamp)
        """
        self._acquire_lock()
        try:
            return (
                self._data['temperature'],
                self._data['humidity'],
                self._data['temp_timestamp']
            )
        finally:
            self._release_lock()
    
    # -------- APC1 Methods --------
    def update_apc1(self, readings):
        """Update APC1 readings from sensor dictionary.
        
        Args:
            readings: Dictionary from apc1.read_all() or None on error
        """
        self._acquire_lock()
        try:
            if readings is None:
                # Mark as error but keep timestamp
                self._data['pm_timestamp'] = time.time()
                return
            
            # Extract values safely with None fallback
            self._data['pm1'] = readings.get('PM1.0', {}).get('value')
            self._data['pm25'] = readings.get('PM2.5', {}).get('value')
            self._data['pm10'] = readings.get('PM10', {}).get('value')
            self._data['tvoc'] = readings.get('TVOC', {}).get('value')
            self._data['eco2'] = readings.get('eCO2', {}).get('value')
            self._data['aqi_tvoc'] = readings.get('AQI', {}).get('value')
            self._data['temp_comp'] = readings.get('T-comp', {}).get('value')
            self._data['rh_comp'] = readings.get('RH-comp', {}).get('value')
            self._data['pm_timestamp'] = time.time()
            
            # Compute AQI from PM2.5 if available
            if self._data['pm25'] is not None:
                from apc1 import APC1
                self._data['aqi_pm25'] = APC1.compute_aqi_pm25(self._data['pm25'])
            else:
                self._data['aqi_pm25'] = None
        finally:
            self._release_lock()
    
    def get_apc1_pm(self):
        """Get particulate matter readings.
        
        Returns:
            tuple: (pm1, pm25, pm10, timestamp)
        """
        self._acquire_lock()
        try:
            return (
                self._data['pm1'],
                self._data['pm25'],
                self._data['pm10'],
                self._data['pm_timestamp']
            )
        finally:
            self._release_lock()
    
    def get_apc1_aqi(self):
        """Get AQI readings (computed from PM2.5 and TVOC-based).
        
        Returns:
            tuple: (aqi_pm25, aqi_tvoc, pm25_value, timestamp)
        """
        self._acquire_lock()
        try:
            return (
                self._data['aqi_pm25'],
                self._data['aqi_tvoc'],
                self._data['pm25'],
                self._data['pm_timestamp']
            )
        finally:
            self._release_lock()
    
    def get_apc1_all(self):
        """Get all APC1 readings as a dictionary (for scrolling display).
        
        Returns:
            dict: All APC1 readings with timestamp
        """
        self._acquire_lock()
        try:
            return {
                'pm1': self._data['pm1'],
                'pm25': self._data['pm25'],
                'pm10': self._data['pm10'],
                'tvoc': self._data['tvoc'],
                'eco2': self._data['eco2'],
                'aqi_tvoc': self._data['aqi_tvoc'],
                'aqi_pm25': self._data['aqi_pm25'],
                'temp_comp': self._data['temp_comp'],
                'rh_comp': self._data['rh_comp'],
                'timestamp': self._data['pm_timestamp']
            }
        finally:
            self._release_lock()
    
    # -------- Battery Methods --------
    def update_battery(self, voltage, percent):
        """Update battery readings.
        
        Args:
            voltage: Battery voltage (or None on error)
            percent: Battery percentage (or None on error)
        """
        self._acquire_lock()
        try:
            self._data['battery_voltage'] = voltage
            self._data['battery_percent'] = percent
            self._data['battery_timestamp'] = time.time()
        finally:
            self._release_lock()
    
    def get_battery(self):
        """Get battery readings.
        
        Returns:
            tuple: (voltage, percent, timestamp)
        """
        self._acquire_lock()
        try:
            return (
                self._data['battery_voltage'],
                self._data['battery_percent'],
                self._data['battery_timestamp']
            )
        finally:
            self._release_lock()
    
    # -------- Utility Methods --------
    def get_all_for_scroll(self):
        """Get all sensor readings formatted for scrolling display.
        
        Returns:
            dict: All sensor readings with timestamps
        """
        self._acquire_lock()
        try:
            return {
                'temperature': self._data['temperature'],
                'humidity': self._data['humidity'],
                'pm25': self._data['pm25'],
                'pm10': self._data['pm10'],
                'aqi_pm25': self._data['aqi_pm25'],
                'battery_voltage': self._data['battery_voltage'],
                'battery_percent': self._data['battery_percent'],
            }
        finally:
            self._release_lock()
    
    def has_shtc3_data(self):
        """Check if SHTC3 data is available."""
        return self._data['temperature'] is not None
    
    def has_apc1_data(self):
        """Check if APC1 data is available."""
        return self._data['pm25'] is not None
    
    def has_battery_data(self):
        """Check if battery data is available."""
        return self._data['battery_voltage'] is not None
