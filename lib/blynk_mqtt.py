# SPDX-FileCopyrightText: 2024 Volodymyr Shymanskyy for Blynk Technologies Inc.
# SPDX-License-Identifier: Apache-2.0
#
# The software is provided "as is", without any warranties or guarantees (explicit or implied).
# This includes no assurances about being fit for any specific purpose.

import gc, sys, time, machine, json, asyncio
from config import load_settings, get_blynk_settings, get_ntp_settings
from umqtt.simple import MQTTClient, MQTTException

# Load Blynk configuration from settings.json
_settings = load_settings()
_blynk_cfg = get_blynk_settings(_settings)
_ntp_cfg = get_ntp_settings(_settings)

# Extract config values for backward compatibility
BLYNK_MQTT_BROKER = _blynk_cfg["mqtt_broker"]
BLYNK_AUTH_TOKEN = _blynk_cfg["auth_token"]
BLYNK_TEMPLATE_ID = _blynk_cfg["template_id"]

# Initialize NTP sync if enabled
_ntp_sync = None
if _ntp_cfg["enabled"]:
    from ntp_helper import NTPSync
    _ntp_sync = NTPSync(
        servers=_ntp_cfg["servers"],
        timezone_offset_hours=_ntp_cfg["timezone_offset_hours"],
        sync_interval_s=_ntp_cfg["sync_interval_s"]
    )

def _dummy(*args):
    pass

on_connected = _dummy
on_disconnected = _dummy
on_message = _dummy
firmware_version = "0.0.1"
connection_count = 0

LOGO = r"""
      ___  __          __
     / _ )/ /_ _____  / /__
    / _  / / // / _ \/  '_/
   /____/_/\_, /_//_/_/\_\
          /___/
"""

print(LOGO)

def _parse_url(url):
    try:
        scheme, url = url.split("://", 1)
    except ValueError:
        scheme = None
    try:
        netloc, path = url.split("/", 1)
    except ValueError:
        netloc, path = url, ""
    try:
        hostname, port = netloc.split(":", 1)
    except:
        hostname = netloc
    return scheme, hostname, int(port), path

def _on_message(topic, payload):
    topic = topic.decode("utf-8")
    payload = payload.decode("utf-8")

    if topic == "downlink/redirect":
        _, mqtt.server, mqtt.port, _ = _parse_url(payload)
        print("Redirecting...")
        mqtt.disconnect()  # Trigger automatic reconnect
    elif topic == "downlink/reboot":
        print("Rebooting...")
        machine.reset()
    elif topic == "downlink/ping":
        pass  # MQTT client library automagically sends the QOS1 response
    else:
        on_message(topic, payload)

ssl_ctx = None
if sys.platform in ("esp32", "rp2", "linux"):
    import ssl
    #print(ssl.MBEDTLS_VERSION)
    ssl_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ssl_ctx.verify_mode = ssl.CERT_REQUIRED
    # ISRG Root X1, expires: Mon, 04 Jun 2035 11:04:38 GMT
    ssl_ctx.load_verify_locations(cafile="ISRG_Root_X1.der")

mqtt = MQTTClient(client_id="", server=BLYNK_MQTT_BROKER, ssl=ssl_ctx,
                  user="device", password=BLYNK_AUTH_TOKEN, keepalive=45)
mqtt.set_callback(_on_message)

async def _mqtt_connect():
    global connection_count

    mqtt.disconnect()
    gc.collect()  # Free memory before MQTT connection
    print("Connecting to MQTT broker...")
    mqtt.connect()
    mqtt.subscribe("downlink/#")
    print("Connected to Blynk.Cloud", "[secure]" if ssl_ctx else "[insecure]")

    info = {
        "type": BLYNK_TEMPLATE_ID,
        "tmpl": BLYNK_TEMPLATE_ID,
        "ver":  firmware_version,
        "rxbuff": 512
    }
    # Send info to the server
    mqtt.publish("info/mcu", json.dumps(info))
    connection_count += 1
    try:
        on_connected()
    except Exception as e:
        sys.print_exception(e)

async def task():
    connected = False
    while True:
        await asyncio.sleep_ms(10)
        if not connected:
            # Sync time before SSL connection if NTP is enabled
            if ssl_ctx and _ntp_sync and not _ntp_sync.is_synced():
                print("NTP sync required for SSL connection...")
                await _ntp_sync.sync_time_async()
            
            # Aggressive GC before MQTT/SSL connection attempt
            gc.collect()
            free_kb = gc.mem_free() / 1024
            print(f"Pre-MQTT memory: {free_kb:.1f}KB free")
            
            try:
                await _mqtt_connect()
                connected = True
            except Exception as e:
                if isinstance(e, OSError):
                    print("Connection failed:", e)
                    await asyncio.sleep(5)
                elif isinstance(e, AttributeError):
                    pass  # This happens during reconnection
                elif isinstance(e, MQTTException) and (e.value == 4 or e.value == 5):
                    print("Invalid BLYNK_AUTH_TOKEN")
                    await asyncio.sleep(15 * 60)
                else:
                    sys.print_exception(e)
                    await asyncio.sleep(5)
        else:
            try:
                mqtt.check_msg()
            except Exception as e:
                #sys.print_exception(e)
                connected = False
                try:
                    on_disconnected()
                except Exception as e:
                    sys.print_exception(e)
