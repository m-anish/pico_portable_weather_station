import network, socket, time

def connect(ssid, password, oled=None):
    wlan = network.WLAN(network.STA_IF)
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
