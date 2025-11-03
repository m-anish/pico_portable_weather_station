import network, socket, time

try:
    import uasyncio as asyncio
except ImportError:
    import asyncio

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
            print("Connected, IP:", ip)
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
    
    print(f"Connecting to WiFi: {ssid}")
    wlan.connect(ssid, password)
    
    # Wait for connection with timeout
    attempts = timeout_s * 2  # Check every 0.5s
    for i in range(attempts):
        if wlan.isconnected():
            ip = wlan.ifconfig()[0]
            print(f"✓ WiFi connected! IP: {ip}")
            if oled:
                oled.fill(0)
                oled.text("WiFi OK!", 0, 0)
                oled.text(ip, 0, 12)
                oled.show()
                # Don't sleep here - could be called before event loop starts
            return True
        await asyncio.sleep(0.5)
    
    # Connection failed
    print("⚠ WiFi connection timeout")
    if oled:
        oled.fill(0)
        oled.text("WiFi timeout", 0, 0)
        oled.text("Continuing...", 0, 12)
        oled.show()
        # Don't sleep here - could be called before event loop starts
    
    wlan.disconnect()
    return False

def disconnect():
    """Disconnect from WiFi."""
    wlan = get_wlan()
    if wlan.active():
        wlan.disconnect()
        wlan.active(False)
    print("WiFi disconnected")

def start_config_ap(ap_ssid="PICO_SETUP", ap_password="12345678", on_save=None, oled=None):
    ap = network.WLAN(network.AP_IF)
    ap.active(True)
    ap.config(essid=ap_ssid, password=ap_password)
    while ap.active() == False:
        pass
    ip = ap.ifconfig()[0]
    print("AP started:", ap_ssid, ip)
    if oled:
        oled.fill(0)
        oled.text("Wi-Fi Setup", 0, 0)
        oled.text(ap_ssid, 0, 12)
        oled.text("Password: 12345678", 0, 24)
        oled.text(ip, 0, 36)
        oled.show()

    html = """<!DOCTYPE html>
<html>
<form action="/" method="POST">
SSID:<br><input name="ssid"><br>
Password:<br><input name="password"><br><br>
<input type="submit" value="Save">
</form>
</html>"""

    addr = socket.getaddrinfo("0.0.0.0", 80)[0][-1]
    s = socket.socket()
    s.bind(addr)
    s.listen(1)
    print("Web config running on", ip)

    while True:
        cl, _ = s.accept()
        req = cl.recv(1024).decode()
        if "POST" in req:
            try:
                data = req.split("\r\n\r\n")[1]
                kv = dict(pair.split("=") for pair in data.split("&"))
                ssid = kv.get("ssid", "")
                password = kv.get("password", "")
                if on_save:
                    on_save(ssid, password)
                cl.send("HTTP/1.0 200 OK\r\n\r\nSaved. Rebooting...")
                cl.close()
                time.sleep(2)
                import machine
                machine.reset()
            except Exception as e:
                print("Form error:", e)
        else:
            cl.send("HTTP/1.0 200 OK\r\n\r\n" + html)
            cl.close()
