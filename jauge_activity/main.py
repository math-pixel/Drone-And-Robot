
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
    
    # --- IMPORTS ---
    from utils.rpi.BandeauLED import BandeauLED # Adapte le chemin selon où tu as mis le fichier
    import board

    NUM_LEDS = 15  # LEDs par bandeau

    # --- CONFIGURATION LED ---
    strips = {
        "happiness": {
            "controller": LEDController(pin=board.D18, num_leds=NUM_LEDS),
            "color": (255, 223, 0)     # Jaune
        },
        "stress": {
            "controller": LEDController(pin=board.D21, num_leds=NUM_LEDS),
            "color": (255, 100, 0)     # Orange
        },
        "shame": {
            "controller": LEDController(pin=board.D12, num_leds=NUM_LEDS),
            "color": (180, 0, 255)     # Violet
        },
        "angry": {
            "controller": LEDController(pin=board.D16, num_leds=NUM_LEDS),
            "color": (255, 0, 0)       # Rouge
        }
    }

    # Définition des steps
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
    # DELEGATE (à personnaliser par l'utilisateur)
    # ======================================================
    
    async def my_action_handler(action: dict, client: WSClient, step_id: int):
        """
        Delegate personnalisé pour gérer les actions.
        L'utilisateur implémente ici son match case.
        """
        action_id = action.get("id")
        action_type = action.get("type")
        
        match action_type:
            case "update_emotion":
                """
                Traite le JSON des émotions et allume les LEDs correspondantes
                
                Args:
                    action: Dict contenant "emotions"
                    ease: Délai animation (0 = instantané)
                """
                emotions = action.get("emotions", [])
                
                for emotion in emotions:
                    emotion_type = emotion.get("type")
                    level = emotion.get("level", 0)
                    
                    if emotion_type not in strips:
                        continue
                    
                    strip = strips[emotion_type]
                    controller = strip["controller"]
                    r, g, b = strip["color"]
                    
                    # Mapper le level en nombre de LEDs
                    num_leds_on = map_level_to_leds(level, NUM_LEDS)
                    
                    # Éteindre le strip puis allumer le bon nombre de LEDs
                    controller.lightsOFF()
                    # todo defined led start index for kept the bottom of the jauge always on
                    if num_leds_on > 0:
                        controller.lightUp(0, num_leds_on - 1, r, g, b, ease)                
            case _:
                print(f"     ⚠️  Unknown action type: {action_type}")

        

    # ======================================================
    # RUN
    # ======================================================
    
    client = WSClient(
        url="ws://192.168.10.182:8057/ws",
        client_key="choice_activity",
        action_delegate=my_action_handler,
        steps=STEPS
    )
    
    asyncio.run(client.run())