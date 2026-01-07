# main.py pour ESP32 MicroPython

import network
import time
from WsClient_iot import WSClient
from ledController import LEDController

# ======================================================
# CONFIG
# ======================================================

WIFI_SSID = "Cudy-F810"
WIFI_PASS = "13022495"
SERVER_URL = "ws://192.168.10.34:8057/ws"

NUMBER_LEDS_BY_COLUMN = 37
NUMBER_COLOMN = 1
NUM_LEDS = NUMBER_COLOMN * NUMBER_LEDS_BY_COLUMN


# ======================================================
# STRIPS CONFIG
# ======================================================

strips = {
    "happiness": {
        "controller": LEDController(pin_num=18, num_leds=NUM_LEDS),
        "color": (255, 255, 255)     # Jaune
    }
}

# ======================================================
# HELPERS
# ======================================================

def map_level_to_leds(level, num_leds):
    """Mappe un level (0-100) sur le nombre de LEDs."""
    level = max(0, min(100, level))  # Clamp 0-100
    return round((level / 100) * num_leds)  # Diviser par 100

def update_leds(score):
    controller = strips["happiness"]["controller"]  # ← Ajoute cette ligne
    
    num_leds_on = map_level_to_leds(score, NUMBER_LEDS_BY_COLUMN)
    controller.lights_off()
    if num_leds_on > 0:
        for i in range(NUMBER_COLOMN):
            start = i * NUMBER_LEDS_BY_COLUMN
            end = start + num_leds_on - 1
            controller.light_up(start, end, 255, 223, 0)

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

# ======================================================
# DELEGATES (pas async!)
# ======================================================

def my_key_handler(data, client):
    """
    Delegate appelé à chaque réception de message.
    ⚠️ Pas de 'async' - c'est une fonction normale!
    """
    key = data.get("key", "")
    
    print(f"🔑 [KEY DELEGATE] Received: {key}")
    
    if key == "update_jauge_score":
        #score = data.get("activity").get("throw_activity").get("score", {})
        #score = data.get("activity", [{}])[0].get("throw_activity", {}).get("score", {})
        activity_list = data.get("activity", [])
        score = 0
        for item in activity_list:
            if "throw_activity" in item:
                score = item["throw_activity"].get("score", 0)
                break
        
        print("score :")
        print(score)
        print("========== data ===========")
        #print(data)
        update_leds(score)


def my_action_handler(action, client, step_id):
    """Gère les actions des steps"""
    action_type = action.get("type")
    print(f"🎬 Action: {action_type}")

# ======================================================
# STEPS
# ======================================================

STEPS = [
    {
        "id": 1, 
        "actions": [
            {"id": 1, "type": "Gauge_throwActivity", "finished": False},
        ], 
        "authorized": False, 
        "finished": False
    },
]

# ======================================================
# MAIN
# ======================================================

def main():
    print("\n" + "="*40)
    print("🚀 ESP32 Throw Jauge Activity")
    print("="*40 + "\n")
    
    # Test LEDs au démarrage
    print("💡 Testing LEDs...")    

    update_leds(50)
    time.sleep(2)
    
    # Éteindre les LEDs
    for strip in strips.values():
        strip["controller"].lights_off()
    
    # Connexion WiFi
    if not connect_wifi():
        return
    
    # Lancement WebSocket
    client = WSClient(
        url=SERVER_URL,
        client_key="jauge_throw_activity",
        action_delegate=my_action_handler,
        key_delegate=my_key_handler,
        steps=STEPS
    )
    
    # ⚠️ Pas de asyncio.run() - juste .run()
    client.run()


# ======================================================
# LANCEMENT
# ======================================================

if __name__ == "__main__":
    main()

