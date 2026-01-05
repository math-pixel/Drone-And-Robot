# main.py pour ESP32 MicroPython

import asyncio
from machine import Pin
from neopixel import NeoPixel
from WsClient_iot import WSClient

# --- CONFIG ---
NUM_LEDS = 37

def map_level_to_leds(level, num_leds):
    level = max(0, min(1, level))
    return round(level * num_leds)


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
        for i in range(start, end + 1):
            self.np[i] = (r, g, b)
        self.np.write()


# --- STRIPS CONFIG ---
# ⚠️ Utilise les numéros GPIO, pas board.Dxx
strips = {
    "happiness": {
        "controller": LEDController(pin_num=18, num_leds=NUM_LEDS),
        "color": (255, 223, 0)     # Jaune
    },
    "stress": {
        "controller": LEDController(pin_num=21, num_leds=NUM_LEDS),
        "color": (255, 100, 0)     # Orange
    },
    "shame": {
        "controller": LEDController(pin_num=12, num_leds=NUM_LEDS),
        "color": (180, 0, 255)     # Violet
    },
    "angry": {
        "controller": LEDController(pin_num=16, num_leds=NUM_LEDS),
        "color": (255, 0, 0)       # Rouge
    }
}


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
        
        num_leds_on = map_level_to_leds(level, NUM_LEDS)
        
        controller.lights_off()
        if num_leds_on > 0:
            controller.light_up(0, num_leds_on - 1, r, g, b)

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

def map_level_to_leds(level, num_leds):
    """
    Mappe un level (0-1) sur le nombre de LEDs à allumer
    
    Args:
        level: Valeur entre 0 et 1
        num_leds: Nombre total de LEDs sur le strip
        
    Returns:
        int: Nombre de LEDs à allumer
    """
    level = max(0, min(1, level))  # Clamp entre 0 et 1
    return round(level * num_leds)



if __name__ == "__main__":
    
    print("Test ESP32 LEDs")
    
    # Test: allumer 50% de chaque jauge
    test_emotions = [
        {"type": "happiness", "level": 1},
        {"type": "stress", "level": 0.3},
        {"type": "shame", "level": 0.7},
        {"type": "angry", "level": 0.2}
    ]
    
    update_emotion(test_emotions)
    print("LEDs allumées!")



    async def my_key_handler(data: dict, client: WSClient):
        """
        Delegate appelé à chaque réception de message.
        Permet de réagir à n'importe quel message du serveur.
        """
        key = data.get("key", "")
        
        print(f"🔑 [KEY DELEGATE] Received: {key}")
        
        # Exemples de traitement personnalisé
        if key == "update_emotions":
            emotions = data.get("emotions", [])
            update_emotion(emotions)
            print(f"   → Emotions received: {len(emotions)} items")
            # Faire quelque chose avec les émotions...
            
    # ======================================================
    # RUN
    # ======================================================
    
    client = WSClient(
        url="ws://192.168.10.182:8057/ws",
        client_key="choice_activity",
        key_delegate=my_key_handler,
        steps=STEPS
    )
    
    asyncio.run(client.run())
