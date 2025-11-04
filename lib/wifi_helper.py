import network, socket, time, machine

try:
    import uasyncio as asyncio
except ImportError:
    import asyncio

import logger

# Global WLAN instance
_wlan = None

def get_wlan():
    """Get the global WLAN instance (creates if needed)."""
    global _wlan
    if _wlan is None:
        _wlan = network.WLAN(network.STA_IF)
    return _wlan

def is_connected():
    """Check if WiFi is currently connected."""
    wlan = get_wlan()
    return wlan.active() and wlan.isconnected()

def get_ip_address():
    """Get the current IP address.
    
    Returns:
        str: IP address if connected, None otherwise
    """
    wlan = get_wlan()
    if wlan.active() and wlan.isconnected():
        return wlan.ifconfig()[0]
    return None

def get_status():
    """Get detailed WiFi status.
    
    Returns:
        dict: Status info with keys: connected, ip, ssid, rssi
    """
    wlan = get_wlan()
    if not wlan.active():
        return {"connected": False, "ip": None, "ssid": None, "rssi": None}
    
    status = {
        "connected": wlan.isconnected(),
        "ip": wlan.ifconfig()[0] if wlan.isconnected() else None,
        "ssid": wlan.config('essid') if wlan.isconnected() else None,
        "rssi": wlan.status('rssi') if wlan.isconnected() else None
    }
    return status

def connect(ssid, password, oled=None):
    """Synchronous WiFi connection (legacy compatibility)."""
    wlan = get_wlan()
    wlan.active(True)
    wlan.connect(ssid, password)
    for _ in range(30):
        if wlan.isconnected():
            ip = wlan.ifconfig()[0]
            logger.info(f"Connected, IP: {ip}")
            if oled:
                oled.text(ip, 0, 36)
                oled.show()
            return True
        time.sleep(0.5)
    wlan.disconnect()
    wlan.active(False)
    return False

async def connect_async(ssid, password, timeout_s=15, oled=None):
    """Async WiFi connection with timeout.
    
    Args:
        ssid: WiFi SSID
        password: WiFi password
        timeout_s: Connection timeout in seconds
        oled: Optional OLED display for status
    
    Returns:
        bool: True if connected, False otherwise
    """
    import gc
    
    wlan = get_wlan()
    wlan.active(True)
    
    # Free memory before WiFi connection
    gc.collect()
    
    if oled:
        oled.fill(0)
        oled.text("WiFi:", 0, 0)
        oled.text(ssid, 0, 12)
        oled.text("Connecting...", 0, 24)
        oled.show()
    
    logger.info(f"Connecting to WiFi: {ssid}")
    wlan.connect(ssid, password)
    
    # Wait for connection with timeout
    attempts = timeout_s * 2  # Check every 0.5s
    for i in range(attempts):
        if wlan.isconnected():
            ip = wlan.ifconfig()[0]
            logger.info(f"✓ WiFi connected! IP: {ip}")
            if oled:
                oled.fill(0)
                oled.text("WiFi OK!", 0, 0)
                oled.text(ip, 0, 12)
                oled.show()
                # Don't sleep here - could be called before event loop starts
            return True
        await asyncio.sleep(0.5)
    
    # Connection failed
    logger.warn("⚠ WiFi connection timeout")
    if oled:
        oled.fill(0)
        oled.text("WiFi timeout", 0, 0)
        oled.text("Continuing...", 0, 12)
        oled.show()
        # Don't sleep here - could be called before event loop starts
    
    # Clean shutdown: disconnect and deactivate interface
    wlan.disconnect()
    wlan.active(False)
    return False

def disconnect():
    """Disconnect from WiFi."""
    wlan = get_wlan()
    if wlan.active():
        wlan.disconnect()
        wlan.active(False)
    logger.info("WiFi disconnected")

def start_config_ap(ap_ssid="PICO_SETUP", ap_password="12345678", on_save=None, oled=None):
    """Start WiFi access point for configuration with robust error handling."""
    try:
        logger.info("Starting AP mode...")
        if oled:
            oled.fill(0)
            oled.text("Starting AP...", 0, 0)
            oled.show()
        
        # Disable station mode first to avoid conflicts
        wlan = get_wlan()
        if wlan.active():
            wlan.active(False)
            logger.info("Disabled station mode")
        
        # Create and configure AP
        ap = network.WLAN(network.AP_IF)
        
        # Reset AP interface to clean state
        ap.active(False)
        time.sleep(0.5)
        
        # Activate AP with error handling
        try:
            ap.active(True)
            logger.info("AP interface activated")
        except Exception as e:
            logger.error(f"Failed to activate AP interface: {e}")
            if oled:
                oled.fill(0)
                oled.text("AP Error!", 0, 0)
                oled.text("Reset device", 0, 12)
                oled.show()
            time.sleep(2)
            machine.reset()
        
        # Wait for AP to be ready with timeout
        ap_ready_timeout = 5  # 5 seconds
        start_time = time.time()
        while not ap.active():
            if time.time() - start_time > ap_ready_timeout:
                logger.error("AP activation timeout")
                if oled:
                    oled.fill(0)
                    oled.text("AP Timeout!", 0, 0)
                    oled.text("Reset device", 0, 12)
                    oled.show()
                time.sleep(2)
                machine.reset()
            time.sleep(0.1)
        
        # Configure AP with error handling
        try:
            ap.config(essid=ap_ssid, password=ap_password)
            logger.info(f"AP configured: {ap_ssid}")
        except Exception as e:
            logger.error(f"Failed to configure AP: {e}")
            if oled:
                oled.fill(0)
                oled.text("AP Config Error!", 0, 0)
                oled.text("Reset device", 0, 12)
                oled.show()
            time.sleep(2)
            machine.reset()
        
        # Get IP address with error handling
        ip = "192.168.4.1"  # Default Pico W AP IP
        try:
            ip = ap.ifconfig()[0]
            logger.info(f"AP IP: {ip}")
        except Exception as e:
            logger.error(f"Failed to get AP IP: {e}")
        
        logger.info(f"AP started successfully: {ap_ssid} @ {ip}")
        
        if oled:
            oled.fill(0)
            oled.text("Wi-Fi Setup", 0, 0)
            oled.text(ap_ssid, 0, 12)
            oled.text("Pwd: 12345678", 0, 24)
            oled.text(ip, 0, 36)
            oled.show()

    except Exception as e:
        logger.error(f"Critical error in AP setup: {e}")
        if oled:
            oled.fill(0)
            oled.text("AP Setup Failed", 0, 0)
            oled.text("Reset device", 0, 12)
            oled.show()
        time.sleep(3)
        machine.reset()

    html = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PicoWeather Setup</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .container {
            background: white;
            border-radius: 12px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            padding: 40px;
            max-width: 400px;
            width: 100%;
        }
        h1 {
            color: #333;
            font-size: 24px;
            margin-bottom: 8px;
            text-align: center;
        }
        .subtitle {
            color: #667eea;
            font-size: 14px;
            text-align: center;
            margin-bottom: 30px;
            font-weight: 500;
        }
        label {
            display: block;
            color: #555;
            font-size: 14px;
            font-weight: 500;
            margin-bottom: 8px;
        }
        input[type="text"],
        input[type="password"] {
            width: 100%;
            padding: 12px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-size: 16px;
            transition: border-color 0.3s;
            margin-bottom: 20px;
        }
        input[type="text"]:focus,
        input[type="password"]:focus {
            outline: none;
            border-color: #667eea;
        }
        input[type="submit"] {
            width: 100%;
            padding: 14px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        input[type="submit"]:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 20px rgba(102, 126, 234, 0.4);
        }
        input[type="submit"]:active {
            transform: translateY(0);
        }
        @media (max-width: 480px) {
            .container { padding: 30px 20px; }
            h1 { font-size: 20px; }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>PicoWeather Initial Setup</h1>
        <div class="subtitle">starstucklab.com</div>
        <form action="/" method="POST">
            <label for="ssid">WiFi Network (SSID)</label>
            <input type="text" id="ssid" name="ssid" required autocomplete="off" placeholder="Enter your WiFi name">
            
            <label for="password">WiFi Password</label>
            <input type="password" id="password" name="password" autocomplete="off" placeholder="Enter your WiFi password">
            
            <input type="submit" value="Save & Connect">
        </form>
    </div>
</body>
</html>"""

    addr = socket.getaddrinfo("0.0.0.0", 80)[0][-1]
    s = socket.socket()
    s.bind(addr)
    s.listen(1)
    logger.info(f"Web config running on {ip}")

    while True:
        cl, _ = s.accept()
        req = cl.recv(1024).decode()
        if "POST" in req:
            try:
                # DIAGNOSTIC LOGGING
                logger.info("="*50)
                logger.info("POST REQUEST RECEIVED")
                logger.info(f"Initial request length: {len(req)} bytes")
                
                # Extract Content-Length if present
                content_length = 0
                for line in req.split("\r\n"):
                    if line.startswith("Content-Length:"):
                        content_length = int(line.split(":")[1].strip())
                        logger.info(f"Content-Length header: {content_length} bytes")
                        break
                
                # Split headers from body
                parts = req.split("\r\n\r\n", 1)
                if len(parts) > 1:
                    headers = parts[0]
                    body = parts[1]
                    logger.info(f"Initial body length: {len(body)} bytes")
                    
                    # If we have Content-Length and body is incomplete, keep reading
                    if content_length > 0 and len(body) < content_length:
                        logger.info(f"Body incomplete, reading more data...")
                        while len(body) < content_length:
                            more_data = cl.recv(1024).decode()
                            body += more_data
                            logger.info(f"Read {len(more_data)} more bytes, total body: {len(body)} bytes")
                            if not more_data:  # Connection closed
                                break
                    
                    data = body
                    logger.info(f"Complete body received: {len(data)} bytes")
                else:
                    data = ""
                    logger.error("Could not find request body separator!")
                
                logger.info(f"Form data: {repr(data)}")
                
                # Parse form data safely, handling edge cases
                kv = {}
                pairs = data.split("&")
                logger.info(f"Split into {len(pairs)} pairs")
                
                for pair in pairs:
                    logger.info(f"Processing pair: {repr(pair)}")
                    if "=" in pair:
                        # Split only on first "=" to handle values containing "="
                        key, value = pair.split("=", 1)
                        logger.info(f"  Key: {repr(key)}, Value (raw): {repr(value)}")
                        
                        # URL decode the value (replace + with space, handle %XX encoding)
                        value = value.replace("+", " ")
                        # Basic URL decoding for common characters
                        try:
                            # Simple percent-decoding for common cases
                            while "%" in value:
                                idx = value.index("%")
                                if idx + 2 < len(value):
                                    hex_str = value[idx+1:idx+3]
                                    try:
                                        char = chr(int(hex_str, 16))
                                        value = value[:idx] + char + value[idx+3:]
                                    except:
                                        break
                                else:
                                    break
                        except:
                            pass  # If decoding fails, use value as-is
                        
                        logger.info(f"  Value (decoded): {repr(value)}")
                        kv[key] = value
                    else:
                        logger.info(f"  Skipping pair (no '='): {repr(pair)}")
                
                logger.info(f"Parsed key-value pairs: {list(kv.keys())}")
                
                ssid = kv.get("ssid", "").strip()
                password = kv.get("password", "").strip()
                
                logger.info(f"Final SSID: {repr(ssid)}, Password length: {len(password)}")
                logger.info("="*50)
                
                if not ssid:
                    logger.error("SSID is empty")
                    cl.send("HTTP/1.0 400 Bad Request\r\n\r\nError: SSID cannot be empty")
                    cl.close()
                    continue
                
                if on_save:
                    on_save(ssid, password)
                cl.send("HTTP/1.0 200 OK\r\n\r\nSaved. Rebooting...")
                cl.close()
                time.sleep(2)
                import machine
                machine.reset()
            except Exception as e:
                logger.error(f"Form error: {e}")
                cl.send("HTTP/1.0 500 Internal Server Error\r\n\r\nError processing form")
                cl.close()
        else:
            cl.send("HTTP/1.0 200 OK\r\n\r\n" + html)
            cl.close()
