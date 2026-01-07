# main.py pour ESP32 MicroPython

import network
import time
from machine import Pin
from neopixel import NeoPixel
from WsClient_iot import WSClient  # ← Assure-toi que ws_client.py est sur l'ESP32

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
# LED CONTROLLER
# ======================================================

class LEDController:
    """Contrôleur NeoPixel pour MicroPython"""
    
    def __init__(self, pin_num, num_leds):
        self.num_leds = num_leds
        self.np = NeoPixel(Pin(pin_num), num_leds)
    
    def lights_off(self):
        for i in range(self.num_leds):
            self.np[i] = (0, 0, 0)
        self.np.write()
    
    def light_up(self, start, end, r, g, b):
        for i in range(start, min(end + 1, self.num_leds)):
            self.np[i] = (r, g, b)
        self.np.write()


# ======================================================
# STRIPS CONFIG
# ======================================================

strips = {
    "happiness": {
        "controller": LEDController(pin_num=18, num_leds=NUM_LEDS),
        "color": (255, 223, 0)     # Jaune
    }
}

# ======================================================
# HELPERS
# ======================================================

def map_level_to_leds(level, num_leds):
    """Mappe un level (0-1) sur le nombre de LEDs à allumer"""
    level = max(0, min(1, level))
    return round(level * num_leds)


def update_emotion(emotions):
    """Met à jour les LEDs selon les émotions"""
    for emotion in emotions:
        emotion_type = emotion.get("type")
        level = emotion.get("level", 0)
        
        if emotion_type not in strips:
            continue
        
        strip = strips[emotion_type]
        controller = strip["controller"]
        r, g, b = strip["color"]
        
        num_leds_on = map_level_to_leds(level, NUMBER_LEDS_BY_COLUMN)
        
        controller.lights_off()
        if num_leds_on > 0:
            for i in range(NUMBER_COLOMN):
                start = i * NUMBER_LEDS_BY_COLUMN
                end = start + num_leds_on - 1
                controller.light_up(start, end, r, g, b)
    
    print("💡 LEDs updated!")


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
        score = data.get("activity").get("throw_activity").get("score", {})
        update_emotion(emotions)


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
    print("🚀 ESP32 Jauge Activity")
    print("="*40 + "\n")
    
    # Test LEDs au démarrage
    print("💡 Testing LEDs...")
    test_emotions = [
        {"type": "happiness", "level": 0.5},
        {"type": "stress", "level": 0.3},
        {"type": "shame", "level": 0.7},
        {"type": "angry", "level": 0.2}
    ]
    update_emotion(test_emotions)
    time.sleep(10)
    
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

