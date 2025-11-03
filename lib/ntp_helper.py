"""ntp_helper.py
Centralized NTP time synchronization for the weather station.

Provides async-friendly NTP sync with configurable servers and timezone support.
Used system-wide for SSL certificate validation, data timestamps, and logging.
"""

import time
try:
    import uasyncio as asyncio
except ImportError:
    import asyncio


class NTPSync:
    """NTP time synchronization manager with timezone support."""
    
    def __init__(self, servers=None, timezone_offset_hours=0.0, sync_interval_s=3600):
        """Initialize NTP sync manager.
        
        Args:
            servers: List of NTP server hostnames (default: ["pool.ntp.org"])
            timezone_offset_hours: Timezone offset from UTC in hours (e.g., 5.5 for IST)
            sync_interval_s: How often to re-sync time (default: 3600 = 1 hour)
        """
        self.servers = servers or ["pool.ntp.org"]
        self.timezone_offset_hours = timezone_offset_hours
        self.timezone_offset_seconds = int(timezone_offset_hours * 3600)
        self.sync_interval_s = sync_interval_s
        self._last_sync = 0
        self._synced = False
    
    def _is_time_valid(self):
        """Check if system time is reasonable (after Jan 2024)."""
        # MicroPython epoch is 2000-01-01 or 1970-01-01 depending on port
        Jan24_epoch2000 = 756_864_000  # Seconds since 2000
        Jan24_epoch1970 = 1_704_067_200  # Seconds since 1970
        
        current_time = time.time()
        gmtime_year = time.gmtime(0)[0]
        
        if gmtime_year == 2000:
            return current_time > Jan24_epoch2000
        else:  # 1970 epoch
            return current_time > Jan24_epoch1970
    
    def sync_time(self, timeout=5):
        """Synchronously sync time with NTP server.
        
        Args:
            timeout: Timeout in seconds for NTP request
        
        Returns:
            bool: True if sync successful, False otherwise
        """
        # Check if already synced recently
        if self._is_time_valid():
            print("System time already valid")
            self._synced = True
            self._last_sync = time.time()
            return True
        
        print("Syncing time with NTP...")
        
        try:
            import ntptime
            
            # Try each server in order
            for server in self.servers:
                try:
                    print(f"  Trying NTP server: {server}")
                    
                    # Set server and timeout
                    ntptime.host = server
                    ntptime.timeout = timeout
                    
                    # Sync time (gets UTC time)
                    ntptime.settime()
                    
                    # Check if sync was successful
                    if self._is_time_valid():
                        utc_time = time.localtime()
                        print(f"  ✓ NTP sync successful")
                        print(f"  UTC time: {self._format_time(utc_time)}")
                        
                        # Apply timezone offset if needed
                        if self.timezone_offset_seconds != 0:
                            # Note: We can't actually change localtime in MicroPython
                            # But we document the offset for display purposes
                            print(f"  Timezone: UTC{self._format_offset()}")
                            print(f"  Local time: {self.get_local_time_str()}")
                        
                        self._synced = True
                        self._last_sync = time.time()
                        return True
                    
                except Exception as e:
                    print(f"  ✗ NTP sync failed with {server}: {e}")
                    continue
            
            print("✗ All NTP servers failed")
            return False
            
        except ImportError:
            print("✗ ntptime module not available")
            return False
        except Exception as e:
            print(f"✗ NTP sync error: {e}")
            return False
    
    async def sync_time_async(self, timeout=5, retry_delay=5, max_retries=3):
        """Asynchronously sync time with NTP server with retries.
        
        Args:
            timeout: Timeout in seconds for each NTP request
            retry_delay: Delay between retries in seconds
            max_retries: Maximum number of retry attempts
        
        Returns:
            bool: True if sync successful, False otherwise
        """
        for attempt in range(max_retries):
            if attempt > 0:
                print(f"NTP sync retry {attempt + 1}/{max_retries}...")
                await asyncio.sleep(retry_delay)
            
            # Run sync in a way that doesn't block other tasks
            if self.sync_time(timeout):
                return True
        
        print(f"✗ NTP sync failed after {max_retries} attempts")
        return False
    
    def is_synced(self):
        """Check if time has been synced."""
        return self._synced
    
    def time_since_sync(self):
        """Get seconds since last successful sync."""
        if not self._synced:
            return None
        return time.time() - self._last_sync
    
    def needs_resync(self):
        """Check if time needs to be resynced based on interval."""
        if not self._synced:
            return True
        return self.time_since_sync() > self.sync_interval_s
    
    def get_local_time(self):
        """Get current local time with timezone offset applied.
        
        Returns:
            time.struct_time: Local time tuple
        """
        # Get UTC time
        utc_seconds = time.time()
        # Apply timezone offset
        local_seconds = utc_seconds + self.timezone_offset_seconds
        return time.localtime(local_seconds)
    
    def get_local_time_str(self):
        """Get formatted local time string.
        
        Returns:
            str: Formatted local time (e.g., "Mon 2024-11-03 17:24:13")
        """
        return self._format_time(self.get_local_time())
    
    def _format_time(self, t):
        """Format time tuple as string.
        
        Args:
            t: time.struct_time tuple
        
        Returns:
            str: Formatted time string
        """
        y, m, d, H, M, S, w, j = t
        days = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
        day_name = days[w]
        return f"{day_name} {y}-{m:02d}-{d:02d} {H:02d}:{M:02d}:{S:02d}"
    
    def _format_offset(self):
        """Format timezone offset as string.
        
        Returns:
            str: Formatted offset (e.g., "+5:30", "-8:00")
        """
        hours = int(self.timezone_offset_hours)
        minutes = int(abs(self.timezone_offset_hours - hours) * 60)
        sign = "+" if self.timezone_offset_hours >= 0 else "-"
        return f"{sign}{abs(hours)}:{minutes:02d}"


# Async task for periodic NTP sync
async def ntp_sync_task(ntp_sync, initial_sync=True):
    """Background task to periodically sync time with NTP.
    
    Args:
        ntp_sync: NTPSync instance
        initial_sync: Whether to perform initial sync before starting periodic sync
    """
    print(f"NTP sync task started (interval: {ntp_sync.sync_interval_s}s)")
    
    # Initial sync if requested
    if initial_sync:
        print("Performing initial NTP sync...")
        await ntp_sync.sync_time_async()
    
    # Periodic re-sync loop
    while True:
        await asyncio.sleep(ntp_sync.sync_interval_s)
        
        if ntp_sync.needs_resync():
            print("Periodic NTP re-sync...")
            await ntp_sync.sync_time_async()
