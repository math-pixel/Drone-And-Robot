import network
import time

WIFI_SSID = "Cudy-F810"
WIFI_PASS = "13022495"
SERVER_URL = "ws://192.168.10.34:8057/ws"


def connect_wifi():
    """Connexion WiFi"""
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    
    if wlan.isconnected():
        print(f"✅ Already connected: {wlan.ifconfig()[0]}")
        return True
    
    print(f"📶 Connecting to {WIFI_SSID}...")
    wlan.connect(WIFI_SSID, WIFI_PASS)
    
    for i in range(20):
        if wlan.isconnected():
            print(f"✅ WiFi connected: {wlan.ifconfig()[0]}")
            return True
        print(".", end="")
        time.sleep(0.5)
    
    print("\n❌ WiFi failed!")
    return False
