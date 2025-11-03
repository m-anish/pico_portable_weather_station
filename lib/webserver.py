"""webserver.py
Async HTTP webserver for Pico Weather Station with chunked responses.

Provides web interface for sensor data viewing and APC1 control.
Integrates with existing power management and sensor cache.
Memory-efficient design with aggressive garbage collection.
"""

try:
    import uasyncio as asyncio
except ImportError:
    import asyncio
import ujson
import gc
import time
from micropython import const

# Constants for memory efficiency
MAX_CONNECTIONS = const(2)
RESPONSE_TIMEOUT = const(30)
CHUNK_SIZE = const(512)
SESSION_TIMEOUT = const(300)  # 5 minutes


class WebSessionManager:
    """Manages web sessions for power-aware APC1 control."""
    
    def __init__(self, timeout_s=SESSION_TIMEOUT):
        """Initialize session manager.
        
        Args:
            timeout_s: Session timeout in seconds
        """
        self.active_sessions = {}
        self.timeout = timeout_s
        self.last_cleanup = time.time()
    
    def register_access(self, client_ip):
        """Register web access and update system activity.
        
        Args:
            client_ip: Client IP address as string
        """
        try:
            self.active_sessions[client_ip] = time.time()
            
            # Trigger system wake-up for web activity
            if hasattr(self, 'wake_callback') and self.wake_callback:
                self.wake_callback("web")
                
        except Exception as e:
            print(f"Session registration error: {e}")
    
    def cleanup_expired(self):
        """Remove expired sessions to prevent memory leaks."""
        try:
            now = time.time()
            
            # Only cleanup periodically to save CPU
            if now - self.last_cleanup < 60:  # Cleanup every minute
                return
            
            expired = []
            for ip, last_access in self.active_sessions.items():
                if now - last_access > self.timeout:
                    expired.append(ip)
            
            for ip in expired:
                del self.active_sessions[ip]
            
            self.last_cleanup = now
            
            if expired:
                print(f"Cleaned up {len(expired)} expired web sessions")
                
        except Exception as e:
            print(f"Session cleanup error: {e}")
    
    def has_active_sessions(self):
        """Check if any web sessions are currently active.
        
        Returns:
            bool: True if active sessions exist
        """
        try:
            self.cleanup_expired()
            return len(self.active_sessions) > 0
        except Exception as e:
            print(f"Session check error: {e}")
            return False
    
    def get_session_count(self):
        """Get count of active sessions.
        
        Returns:
            int: Number of active sessions
        """
        try:
            self.cleanup_expired()
            return len(self.active_sessions)
        except Exception as e:
            print(f"Session count error: {e}")
            return 0


class WebServer:
    """Async HTTP webserver for weather station data."""
    
    def __init__(self, sensor_cache, apc1_power=None, wake_callback=None, config=None):
        """Initialize webserver.
        
        Args:
            sensor_cache: SensorCache instance for data access
            apc1_power: APC1Power instance for sensor control
            wake_callback: Function to call on web activity
            config: Webserver configuration dict
        """
        self.cache = sensor_cache
        self.apc1_power = apc1_power
        self.wake_callback = wake_callback
        self.config = config or {}
        
        # Configuration with defaults
        self.port = self.config.get('port', 80)
        self.session_timeout = self.config.get('session_timeout_s', SESSION_TIMEOUT)
        self.refresh_interval = self.config.get('refresh_interval_s', 20)
        self.max_connections = self.config.get('max_connections', MAX_CONNECTIONS)
        self.chunk_size = self.config.get('chunk_size', CHUNK_SIZE)
        
        # Session management
        self.sessions = WebSessionManager(self.session_timeout)
        if wake_callback:
            self.sessions.wake_callback = wake_callback
        
        # Server state
        self.server = None
        self.running = False
        self.active_connections = 0
        
        # Cache HTML template to avoid rebuilding
        self._html_template = None
        self._css_styles = None
        
        # Power states getter (to be injected)
        self.get_power_states = None
        
        print(f"WebServer initialized (port: {self.port}, max_connections: {self.max_connections})")
    
    def _get_html_template(self):
        """Generate HTML template with responsive design.
        
        Returns:
            str: Complete HTML page template
        """
        if self._html_template is None:
            try:
                css = self._get_css_styles()
                refresh_interval = self.refresh_interval
                
                self._html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pico Weather Station</title>
    <style>{css}</style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🌤️ Pico Weather Station</h1>
            <div class="status-bar">
                <span id="connection-status">🟢 Connected</span>
                <span id="last-update">Loading...</span>
            </div>
        </header>
        
        <main>
            <section class="sensor-grid">
                <div class="sensor-card temperature">
                    <h3>🌡️ Temperature</h3>
                    <div class="value" id="temperature">--°C</div>
                    <div class="timestamp" id="temp-time">--</div>
                </div>
                
                <div class="sensor-card humidity">
                    <h3>💧 Humidity</h3>
                    <div class="value" id="humidity">--%</div>
                    <div class="timestamp" id="humid-time">--</div>
                </div>
                
                <div class="sensor-card pm25">
                    <h3>🫧 PM2.5</h3>
                    <div class="value" id="pm25">-- µg/m³</div>
                    <div class="timestamp" id="pm25-time">--</div>
                </div>
                
                <div class="sensor-card pm10">
                    <h3>🫧 PM10</h3>
                    <div class="value" id="pm10">-- µg/m³</div>
                    <div class="timestamp" id="pm10-time">--</div>
                </div>
                
                <div class="sensor-card tvoc">
                    <h3>🌫️ TVOC</h3>
                    <div class="value" id="tvoc">-- ppb</div>
                    <div class="timestamp" id="tvoc-time">--</div>
                </div>
                
                <div class="sensor-card eco2">
                    <h3>💨 eCO2</h3>
                    <div class="value" id="eco2">-- ppm</div>
                    <div class="timestamp" id="eco2-time">--</div>
                </div>
                
                <div class="sensor-card aqi">
                    <h3>📊 AQI</h3>
                    <div class="value" id="aqi">--</div>
                    <div class="timestamp" id="aqi-time">--</div>
                </div>
                
                <div class="sensor-card battery">
                    <h3>🔋 Battery</h3>
                    <div class="value" id="battery">--V (--%)</div>
                    <div class="timestamp" id="battery-time">--</div>
                </div>
            </section>
            
            <section class="control-panel">
                <h2>System Control</h2>
                <div class="control-grid">
                    <div class="control-item">
                        <h3>APC1 Sensor</h3>
                        <div class="status" id="apc1-status">Checking...</div>
                        <button id="wake-apc1" onclick="wakeAPC1()">Wake APC1</button>
                    </div>
                    
                    <div class="control-item">
                        <h3>Display</h3>
                        <div class="status" id="display-status">Checking...</div>
                    </div>
                    
                    <div class="control-item">
                        <h3>System Info</h3>
                        <div class="info" id="system-info">Loading...</div>
                    </div>
                </div>
            </section>
        </main>
        
        <footer>
            <p>Pico Weather Station | Auto-refresh every {refresh_interval}s</p>
            <p id="debug-info"></p>
        </footer>
    </div>
    
    <script>
        let lastDataTime = 0;
        
        function formatTimeAgo(timestamp) {{
            if (!timestamp) return '--';
            
            const now = Math.floor(Date.now() / 1000);
            const secondsAgo = now - timestamp;
            
            // Handle future timestamps (clock skew)
            if (secondsAgo < 0) return 'just now';
            
            // Less than 1 minute
            if (secondsAgo < 60) {{
                return secondsAgo === 1 ? '1 second ago' : `${{secondsAgo}} seconds ago`;
            }}
            
            // Less than 1 hour (show minutes)
            if (secondsAgo < 3600) {{
                const minutes = Math.floor(secondsAgo / 60);
                return minutes === 1 ? '1 minute ago' : `${{minutes}} minutes ago`;
            }}
            
            // Less than 1 day (show hours and minutes)
            if (secondsAgo < 86400) {{
                const hours = Math.floor(secondsAgo / 3600);
                const minutes = Math.floor((secondsAgo % 3600) / 60);
                if (minutes === 0) {{
                    return hours === 1 ? '1 hour ago' : `${{hours}} hours ago`;
                }}
                return `${{hours}}hr${{minutes}}min ago`;
            }}
            
            // 1 day or more (show days)
            const days = Math.floor(secondsAgo / 86400);
            const hours = Math.floor((secondsAgo % 86400) / 3600);
            if (hours === 0) {{
                return days === 1 ? '1 day ago' : `${{days}} days ago`;
            }}
            return `${{days}}d${{hours}}h ago`;
        }}
        
        function formatAge(timestamp) {{
            if (!timestamp) return 'class="old"';
            const age = Math.floor(Date.now() / 1000) - timestamp;
            if (age < 60) return 'class="fresh"';
            if (age < 300) return 'class="stale"';
            return 'class="old"';
        }}
        
        function updateSensorDisplay(data) {{
            try {{
                document.getElementById('temperature').innerHTML = 
                    data.temperature ? `${{data.temperature.toFixed(1)}}°C` : '--°C';
                document.getElementById('humidity').innerHTML = 
                    data.humidity ? `${{data.humidity.toFixed(1)}}%` : '--%';
                
                document.getElementById('pm25').innerHTML = 
                    data.pm25 ? `${{data.pm25.toFixed(0)}} µg/m³` : '-- µg/m³';
                document.getElementById('pm10').innerHTML = 
                    data.pm10 ? `${{data.pm10.toFixed(0)}} µg/m³` : '-- µg/m³';
                
                document.getElementById('tvoc').innerHTML = 
                    data.tvoc ? `${{data.tvoc.toFixed(0)}} ppb` : '-- ppb';
                document.getElementById('eco2').innerHTML = 
                    data.eco2 ? `${{data.eco2.toFixed(0)}} ppm` : '-- ppm';
                
                document.getElementById('aqi').innerHTML = 
                    data.aqi_pm25 ? Math.floor(data.aqi_pm25) : '--';
                
                document.getElementById('battery').innerHTML = 
                    data.battery_voltage ? `${{data.battery_voltage.toFixed(2)}}V (${{data.battery_percent.toFixed(0)}}%)` : '--V (--%)';
                
                const tempAge = formatAge(data.temp_timestamp);
                document.getElementById('temp-time').innerHTML = `<span ${{tempAge}}>${{formatTimeAgo(data.temp_timestamp)}}</span>`;
                document.getElementById('humid-time').innerHTML = `<span ${{tempAge}}>${{formatTimeAgo(data.temp_timestamp)}}</span>`;
                
                const pmAge = formatAge(data.pm_timestamp);
                document.getElementById('pm25-time').innerHTML = `<span ${{pmAge}}>${{formatTimeAgo(data.pm_timestamp)}}</span>`;
                document.getElementById('pm10-time').innerHTML = `<span ${{pmAge}}>${{formatTimeAgo(data.pm_timestamp)}}</span>`;
                document.getElementById('tvoc-time').innerHTML = `<span ${{pmAge}}>${{formatTimeAgo(data.pm_timestamp)}}</span>`;
                document.getElementById('eco2-time').innerHTML = `<span ${{pmAge}}>${{formatTimeAgo(data.pm_timestamp)}}</span>`;
                document.getElementById('aqi-time').innerHTML = `<span ${{pmAge}}>${{formatTimeAgo(data.pm_timestamp)}}</span>`;
                
                const battAge = formatAge(data.battery_timestamp);
                document.getElementById('battery-time').innerHTML = `<span ${{battAge}}>${{formatTimeAgo(data.battery_timestamp)}}</span>`;
                
                document.getElementById('last-update').textContent = `Updated ${{formatTimeAgo(Math.floor(Date.now() / 1000))}}`;
                lastDataTime = Date.now();
                
            }} catch (error) {{
                console.error('Display update error:', error);
            }}
        }}
        
        function updateSystemStatus(status) {{
            try {{
                document.getElementById('apc1-status').textContent = status.apc1_awake ? 'Awake' : 'Sleeping';
                document.getElementById('display-status').textContent = status.display_on ? 'On' : 'Off';
                
                const systemInfo = `WiFi: ${{status.wifi_connected ? 'Connected' : 'Disconnected'}}\\nIP: ${{status.ip_address || 'N/A'}}\\nFree RAM: ${{status.free_memory || 'N/A'}}KB\\nUptime: ${{status.uptime || 'N/A'}}s`;
                document.getElementById('system-info').textContent = systemInfo;
                
            }} catch (error) {{
                console.error('Status update error:', error);
            }}
        }}
        
        function wakeAPC1() {{
            const button = document.getElementById('wake-apc1');
            button.disabled = true;
            button.textContent = 'Waking...';
            
            fetch('/api/wake')
                .then(response => response.json())
                .then(data => {{
                    if (data.status === 'ok') {{
                        button.textContent = 'Waking...';
                        setTimeout(() => {{
                            button.disabled = false;
                            button.textContent = 'Wake APC1';
                        }}, 5000);
                    }} else {{
                        button.textContent = 'Error';
                        setTimeout(() => {{
                            button.disabled = false;
                            button.textContent = 'Wake APC1';
                        }}, 2000);
                    }}
                }})
                .catch(error => {{
                    console.error('Wake error:', error);
                    button.textContent = 'Error';
                    setTimeout(() => {{
                        button.disabled = false;
                        button.textContent = 'Wake APC1';
                    }}, 2000);
                }});
        }}
        
        function fetchData() {{
            fetch('/api/data')
                .then(response => response.json())
                .then(data => updateSensorDisplay(data))
                .catch(error => {{
                    console.error('Data fetch error:', error);
                    document.getElementById('connection-status').textContent = '🔴 Error';
                }});
        }}
        
        function fetchStatus() {{
            fetch('/api/status')
                .then(response => response.json())
                .then(data => {{
                    updateSystemStatus(data);
                    document.getElementById('connection-status').textContent = '🟢 Connected';
                }})
                .catch(error => {{
                    console.error('Status fetch error:', error);
                    document.getElementById('connection-status').textContent = '🔴 Error';
                }});
        }}
        
        function sendHeartbeat() {{
            fetch('/api/heartbeat')
                .then(response => response.json())
                .catch(error => console.error('Heartbeat error:', error));
        }}
        
        function init() {{
            fetchData();
            fetchStatus();
            
            setInterval(fetchData, {refresh_interval * 1000});
            setInterval(fetchStatus, {refresh_interval * 1000});
            setInterval(sendHeartbeat, 30000);
        }}
        
        if (document.readyState === 'loading') {{
            document.addEventListener('DOMContentLoaded', init);
        }} else {{
            init();
        }}
    </script>
</body>
</html>"""
                
            except Exception as e:
                print(f"HTML template generation error: {e}")
                self._html_template = "<html><body><h1>Template Error</h1></body></html>"
        
        return self._html_template
    
    def _get_css_styles(self):
        """Generate CSS styles for responsive design."""
        if self._css_styles is None:
            self._css_styles = """* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; }
.container { max-width: 1200px; margin: 0 auto; padding: 20px; }
header { background: rgba(255, 255, 255, 0.95); border-radius: 15px; padding: 20px; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); }
h1 { color: #2c3e50; margin-bottom: 10px; font-size: 2.5em; }
.status-bar { display: flex; justify-content: space-between; align-items: center; font-size: 0.9em; color: #666; }
.sensor-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 30px; }
.sensor-card { background: rgba(255, 255, 255, 0.95); border-radius: 15px; padding: 20px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); transition: transform 0.2s ease; }
.sensor-card:hover { transform: translateY(-2px); }
.sensor-card h3 { color: #2c3e50; margin-bottom: 10px; font-size: 1.2em; }
.value { font-size: 2em; font-weight: bold; color: #3498db; margin-bottom: 5px; }
.timestamp { font-size: 0.8em; color: #666; }
.timestamp .fresh { color: #27ae60; }
.timestamp .stale { color: #f39c12; }
.timestamp .old { color: #e74c3c; }
.control-panel { background: rgba(255, 255, 255, 0.95); border-radius: 15px; padding: 20px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); }
.control-panel h2 { color: #2c3e50; margin-bottom: 20px; }
.control-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
.control-item { background: #f8f9fa; border-radius: 10px; padding: 15px; }
.control-item h3 { color: #2c3e50; margin-bottom: 10px; }
.status { font-size: 1.1em; font-weight: bold; margin-bottom: 10px; }
.info { font-size: 0.9em; color: #666; white-space: pre-line; }
button { background: #3498db; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; font-size: 1em; transition: background 0.2s ease; }
button:hover:not(:disabled) { background: #2980b9; }
button:disabled { background: #95a5a6; cursor: not-allowed; }
footer { background: rgba(255, 255, 255, 0.95); border-radius: 15px; padding: 15px; margin-top: 20px; text-align: center; color: #666; font-size: 0.9em; }
@media (max-width: 768px) { .container { padding: 10px; } h1 { font-size: 2em; } .sensor-grid { grid-template-columns: 1fr; } .control-grid { grid-template-columns: 1fr; } .value { font-size: 1.5em; } }"""
        
        return self._css_styles
    
    def _get_sensor_data(self):
        """Get all sensor data from cache."""
        try:
            data = {}
            
            # SHTC3 data
            temp, humid, temp_ts = self.cache.get_shtc3()
            data['temperature'] = temp
            data['humidity'] = humid
            data['temp_timestamp'] = temp_ts
            
            # APC1 data
            pm1, pm25, pm10, pm_ts = self.cache.get_apc1_pm()
            data['pm1'] = pm1
            data['pm25'] = pm25
            data['pm10'] = pm10
            data['pm_timestamp'] = pm_ts
            
            # Gas data
            tvoc, eco2, _ = self.cache.get_apc1_gases()
            data['tvoc'] = tvoc
            data['eco2'] = eco2
            
            # AQI data
            aqi_pm25, aqi_tvoc, _, _ = self.cache.get_apc1_aqi()
            data['aqi_pm25'] = aqi_pm25
            data['aqi_tvoc'] = aqi_tvoc
            
            # Battery data
            voltage, percent, batt_ts = self.cache.get_battery()
            data['battery_voltage'] = voltage
            data['battery_percent'] = percent
            data['battery_timestamp'] = batt_ts
            
            return data
            
        except Exception as e:
            print(f"Sensor data error: {e}")
            return {}
    
    def _get_system_status(self):
        """Get system status information."""
        try:
            status = {}
            
            # Power states (injected during initialization)
            if self.get_power_states:
                status.update(self.get_power_states())
            
            # WiFi status
            try:
                import wifi_helper
                status['wifi_connected'] = wifi_helper.is_connected()
                if status['wifi_connected']:
                    import network
                    sta = network.WLAN(network.STA_IF)
                    status['ip_address'] = sta.ifconfig()[0] if sta.active() else None
                else:
                    status['ip_address'] = None
            except Exception:
                status['wifi_connected'] = False
                status['ip_address'] = None
            
            # Memory info
            try:
                gc.collect()
                status['free_memory'] = gc.mem_free() // 1024
                status['used_memory'] = gc.mem_alloc() // 1024
            except Exception:
                status['free_memory'] = None
                status['used_memory'] = None
            
            # Uptime
            try:
                status['uptime'] = int(time.time())
            except Exception:
                status['uptime'] = None
            
            # Web sessions
            status['active_sessions'] = self.sessions.get_session_count()
            
            return status
            
        except Exception as e:
            print(f"System status error: {e}")
            return {}
    
    async def _send_response(self, writer, status_code, headers, content):
        """Send HTTP response with chunked encoding."""
        try:
            # Status line
            status_text = {
                200: "OK", 201: "Created", 400: "Bad Request",
                404: "Not Found", 500: "Internal Server Error"
            }.get(status_code, "Unknown")
            
            status_line = f"HTTP/1.1 {status_code} {status_text}\r\n"
            writer.write(status_line.encode())
            
            # Headers with chunked encoding
            headers['Transfer-Encoding'] = 'chunked'
            for header, value in headers.items():
                writer.write(f"{header}: {value}\r\n".encode())
            
            writer.write(b"\r\n")
            
            # Convert content to bytes
            if isinstance(content, str):
                content = content.encode()
            
            # Send chunks
            for i in range(0, len(content), self.chunk_size):
                chunk = content[i:i + self.chunk_size]
                writer.write(f"{len(chunk):x}\r\n".encode())
                writer.write(chunk)
                writer.write(b"\r\n")
                await writer.drain()
            
            # Final chunk
            writer.write(b"0\r\n\r\n")
            await writer.drain()
            
        except Exception as e:
            print(f"Send response error: {e}")
    
    async def _handle_request(self, reader, writer):
        """Handle individual HTTP request."""
        client_ip = "unknown"
        try:
            # Get client IP
            peername = writer.get_extra_info('peername')
            if peername:
                client_ip = peername[0]
            
            # Register session access
            self.sessions.register_access(client_ip)
            
            # Read request line
            request_line = await reader.readline()
            if not request_line:
                return
            
            request_line = request_line.decode().strip()
            if not request_line:
                return
            
            # Parse request
            parts = request_line.split(' ')
            if len(parts) < 2:
                await self._send_error(writer, 400, "Bad Request")
                return
            
            method, path = parts[0], parts[1]
            
            # Read headers (skip for efficiency)
            while True:
                header_line = await reader.readline()
                if not header_line or header_line == b"\r\n":
                    break
            
            # Route request
            if path == '/' or path == '/index.html':
                await self._handle_main_page(writer)
            elif path == '/api/data':
                await self._handle_api_data(writer)
            elif path == '/api/status':
                await self._handle_api_status(writer)
            elif path == '/api/heartbeat':
                await self._handle_api_heartbeat(writer, client_ip)
            elif path == '/api/wake':
                await self._handle_api_wake(writer)
            else:
                await self._send_error(writer, 404, "Not Found")
                
        except Exception as e:
            print(f"Request error from {client_ip}: {e}")
        finally:
            try:
                await writer.wait_closed()
            except Exception:
                pass
            self.active_connections -= 1
    
    async def _handle_main_page(self, writer):
        """Handle main page request."""
        try:
            html_content = self._get_html_template()
            headers = {
                'Content-Type': 'text/html; charset=utf-8',
                'Cache-Control': 'no-cache'
            }
            await self._send_response(writer, 200, headers, html_content)
        except Exception as e:
            print(f"Main page error: {e}")
            await self._send_error(writer, 500, "Internal Server Error")
    
    async def _handle_api_data(self, writer):
        """Handle API data request."""
        try:
            data = self._get_sensor_data()
            json_content = ujson.dumps(data)
            headers = {
                'Content-Type': 'application/json',
                'Cache-Control': 'no-cache'
            }
            await self._send_response(writer, 200, headers, json_content)
        except Exception as e:
            print(f"API data error: {e}")
            await self._send_error(writer, 500, "Internal Server Error")
    
    async def _handle_api_status(self, writer):
        """Handle API status request."""
        try:
            status = self._get_system_status()
            json_content = ujson.dumps(status)
            headers = {
                'Content-Type': 'application/json',
                'Cache-Control': 'no-cache'
            }
            await self._send_response(writer, 200, headers, json_content)
        except Exception as e:
            print(f"API status error: {e}")
            await self._send_error(writer, 500, "Internal Server Error")
    
    async def _handle_api_heartbeat(self, writer, client_ip):
        """Handle heartbeat request."""
        try:
            self.sessions.register_access(client_ip)
            
            response = {
                'status': 'ok',
                'timestamp': time.time(),
                'active_sessions': self.sessions.get_session_count()
            }
            
            json_content = ujson.dumps(response)
            headers = {
                'Content-Type': 'application/json',
                'Cache-Control': 'no-cache'
            }
            await self._send_response(writer, 200, headers, json_content)
        except Exception as e:
            print(f"Heartbeat error: {e}")
            await self._send_error(writer, 500, "Internal Server Error")
    
    async def _handle_api_wake(self, writer):
        """Handle APC1 wake request."""
        try:
            if self.apc1_power:
                self.apc1_power.enable()
                
                if self.wake_callback:
                    self.wake_callback("web_wake")
                
                response = {
                    'status': 'ok',
                    'message': 'APC1 wake initiated',
                    'timestamp': time.time()
                }
            else:
                response = {
                    'status': 'error',
                    'message': 'APC1 power control not available'
                }
            
            json_content = ujson.dumps(response)
            headers = {
                'Content-Type': 'application/json',
                'Cache-Control': 'no-cache'
            }
            await self._send_response(writer, 200, headers, json_content)
        except Exception as e:
            print(f"APC1 wake error: {e}")
            await self._send_error(writer, 500, "Internal Server Error")
    
    async def _send_error(self, writer, status_code, message):
        """Send error response."""
        try:
            error_html = f"""<!DOCTYPE html>
<html>
<head><title>Error {status_code}</title></head>
<body>
    <h1>Error {status_code}</h1>
    <p>{message}</p>
    <hr>
    <p>Pico Weather Station</p>
</body>
</html>"""
            
            headers = {'Content-Type': 'text/html'}
            await self._send_response(writer, status_code, headers, error_html)
        except Exception as e:
            print(f"Error response failed: {e}")
    
    async def _client_handler(self, reader, writer):
        """Handle client connection with connection tracking."""
        self.active_connections += 1
        try:
            await asyncio.wait_for(
                self._handle_request(reader, writer),
                timeout=RESPONSE_TIMEOUT
            )
        except asyncio.TimeoutError:
            print("Client timeout")
        except Exception as e:
            print(f"Client handler error: {e}")
        finally:
            self.active_connections -= 1
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass
    
    async def start(self):
        """Start the webserver."""
        try:
            self.running = True
            self.server = await asyncio.start_server(
                self._client_handler,
                '0.0.0.0',
                self.port
            )
            print(f"WebServer started on port {self.port}")
        except Exception as e:
            print(f"WebServer start error: {e}")
            self.running = False
            raise
    
    async def stop(self):
        """Stop the webserver."""
        try:
            self.running = False
            if self.server:
                self.server.close()
                await self.server.wait_closed()
            print("WebServer stopped")
        except Exception as e:
            print(f"WebServer stop error: {e}")


# Webserver task for integration with main async loop
async def webserver_task(sensor_cache, apc1_power=None, wake_callback=None, config=None):
    """Webserver task for integration with main async loop.
    
    Args:
        sensor_cache: SensorCache instance
        apc1_power: APC1Power instance
        wake_callback: Function to call on web activity
        config: Webserver configuration
        
    Returns:
        WebSessionManager: Session manager for web presence detection
    """
    webserver = None
    
    try:
        # Create webserver instance
        webserver = WebServer(sensor_cache, apc1_power, wake_callback, config)
        
        # Start webserver
        await webserver.start()
        
        # Keep task running
        while webserver.running:
            await asyncio.sleep(1)
            
    except Exception as e:
        print(f"Webserver task error: {e}")
    finally:
        if webserver:
            await webserver.stop()
    
    # Return session manager for web presence detection
    return webserver.sessions if webserver else None
