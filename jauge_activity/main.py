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
NUMBER_COLOMN = 3
NUM_LEDS = NUMBER_COLOMN * NUMBER_LEDS_BY_COLUMN

# ======================================================
# STRIPS CONFIG
# ======================================================

strips = {
    "happiness": {
        "controller": LEDController(
            pin_num=18, 
            num_leds=NUM_LEDS,
            num_columns=NUMBER_COLOMN,
            leds_by_column=NUMBER_LEDS_BY_COLUMN,
            flip_vertical=True
        ),
        "color": (255, 223, 0)     # Jaune
    },
    "stress": {
        "controller": LEDController(
            pin_num=21, 
            num_leds=NUM_LEDS,
            num_columns=NUMBER_COLOMN,
            leds_by_column=NUMBER_LEDS_BY_COLUMN,
            flip_vertical=True
        ),
        "color": (255, 100, 0)     # Orange
    },
    "shame": {
        "controller": LEDController(
            pin_num=12, 
            num_leds=NUM_LEDS,
            num_columns=NUMBER_COLOMN,
            leds_by_column=NUMBER_LEDS_BY_COLUMN,
            flip_vertical=True
        ),
        "color": (180, 0, 255)     # Violet
    },
    "angry": {
        "controller": LEDController(
            pin_num=16, 
            num_leds=NUM_LEDS,
            num_columns=NUMBER_COLOMN,
            leds_by_column=NUMBER_LEDS_BY_COLUMN,
            flip_vertical=True
        ),
        "color": (255, 0, 0)       # Rouge
    }
}

# ======================================================
# HELPERS
# ======================================================

def map_level_to_leds(level, num_leds):
    """Mappe un level (0-1) sur le nombre de LEDs à allumer"""
    level = max(0, min(1, level))
    return round(level * num_leds)


def update_emotion(emotions, delay=0.03):
    """Met à jour les LEDs selon les émotions avec animation fluide"""
    for emotion in emotions:
        emotion_type = emotion.get("type")
        level = emotion.get("level", 0)
        
        if emotion_type not in strips:
            continue
        
        strip = strips[emotion_type]
        controller = strip["controller"]
        r, g, b = strip["color"]
        
        num_leds_on = map_level_to_leds(level, NUMBER_LEDS_BY_COLUMN)
        
        # Animation fluide
        controller.set_level(num_leds_on, r, g, b, delay)
    
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
# DELEGATES
# ======================================================

def my_key_handler(data, client):
    key = data.get("key", "")
    print(f"🔑 [KEY DELEGATE] Received: {key}")
    
    if key == "update_emotions":
        emotions = data.get("emotions", [])
        update_emotion(emotions)


def my_action_handler(action, client, step_id):
    action_type = action.get("type")
    print(f"🎬 Action: {action_type}")

# ======================================================
# STEPS
# ======================================================

STEPS = [
    {
        "id": 1, 
        "actions": [
            {"id": 1, "type": "video", "file": "classe.mp4", "finished": False},
            {"id": 2, "type": "choice", "options": [
                {"id": 1, "text": "Passer plus tard"},
                {"id": 2, "text": "Aller direct au tableau"}
            ], "finished": False}
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
    update_emotion(test_emotions, delay=0.05)  # Animation lente pour le test
    time.sleep(2)
    
    # Test descente
    print("💡 Testing descent...")
    test_emotions_low = [
        {"type": "happiness", "level": 0.1},
        {"type": "stress", "level": 0.1},
        {"type": "shame", "level": 0.1},
        {"type": "angry", "level": 0.1}
    ]
    update_emotion(test_emotions_low, delay=0.05)
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
        client_key="jauge_activity",
        action_delegate=my_action_handler,
        key_delegate=my_key_handler,
        steps=STEPS
    )
    
    client.run()


# ======================================================
# LANCEMENT
# ======================================================

if __name__ == "__main__":
    main()
