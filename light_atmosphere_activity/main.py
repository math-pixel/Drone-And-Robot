import asyncio
import time
import os, sys
from stupidArtnet import StupidArtnet

# --- BLOC MAGIQUE A METTRE TOUT EN HAUT ---
current_path = os.path.abspath(__file__)
current_dir = os.path.dirname(current_path)
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from utils.DMX.DMXController import DMXController

# --- 2. Configuration des Lumières ---

# Configuration DMX
DMX_IP = "127.0.0.1" # Change l'IP si QLC+ est sur un autre PC
CHANNELS_PER_LIGHT = 7 # Chaque lumière occupe 7 canaux

# Mapping des émotions vers les couleurs et IDs
# J'ai attribué un ID numérique (1, 2, 3, 4) pour correspondre à tes clés WS
LIGHTS_CONFIG = {
    1: {"name": "happiness", "color": (255, 223, 0)},   # Jaune
    2: {"name": "stress",    "color": (255, 100, 0)},   # Orange
    3: {"name": "shame",     "color": (180, 0, 255)},   # Violet
    4: {"name": "angry",     "color": (255, 0, 0)}      # Rouge
}

# Initialisation du contrôleur DMX
dmx = DMXController(target_ip=DMX_IP, universe=0)

# --- 3. Fonctions Logiques DMX ---

def get_start_address(light_id):
    """Calcule l'adresse de départ DMX en fonction de l'ID de la lampe (1, 2, 3, 4)"""
    # ID 1 -> Address 1
    # ID 2 -> Address 8 (1 + 7)
    # ID 3 -> Address 15 (8 + 7)
    return 1 + ((light_id - 1) * CHANNELS_PER_LIGHT)

def init_lights_sequence():
    """Configure les couleurs, allume 5s, puis éteint"""
    print("💡 [INIT] Configuration des couleurs et allumage test...")
    
    for light_id, data in LIGHTS_CONFIG.items():
        addr = get_start_address(light_id)
        color = data["color"]
        
        # 1. On définit la couleur (Canaux R, G, B)
        dmx.set_rgb(addr, color)
        
        # 2. On allume le Dimmer (Canal 1 de la fixture)
        dmx.set(addr, 255) 
        print(f"   -> Light {light_id} ({data['name']}) : Couleur définie et ON")

    # Attendre 5 secondes
    time.sleep(5)

    print("💡 [INIT] Extinction des lumières (Blackout Brightness)...")
    for light_id in LIGHTS_CONFIG:
        addr = get_start_address(light_id)
        # On met juste le Dimmer à 0, on garde la couleur en mémoire
        dmx.set(addr, 0)

# --- 4. Websocket Handlers ---

def update_light_state(light_id, state):
    """Change l'état (ON/OFF) d'une lumière spécifique via DMX"""
    if light_id not in LIGHTS_CONFIG:
        print(f"⚠️ Light ID {light_id} inconnu.")
        return

    addr = get_start_address(light_id)
    brightness = 255 if state == "on" else 0
    
    # On change uniquement le canal 1 (Brightness) de la fixture
    dmx.set(addr, brightness)
    print(f"🎛️ [DMX] Light {light_id} -> {state.upper()} (Addr {addr} set to {brightness})")


def my_key_handler(data, client):
    """Gère les messages reçus du WebSocket"""
    key = data.get("key", "")
    # print(f"🔑 [WS] Reçu: {key}") # Decommente si tu veux voir tout le traffic
    
    # Format attendu: update_light_{id}_{state}
    # Exemple: update_light_1_on
    if key.startswith("update_light_"):
        try:
            parts = key.split("_")
            # parts = ['update', 'light', '1', 'on']
            if len(parts) == 4:
                light_id = int(parts[2])
                state = parts[3] # 'on' ou 'off'
                
                if state in ["on", "off"]:
                    update_light_state(light_id, state)
                else:
                    print(f"⚠️ État invalide: {state}")
        except ValueError:
            print(f"⚠️ Erreur de parsing sur la clé: {key}")

def my_action_handler(data, client):
    # Delegate vide si tu n'en as pas besoin pour l'instant
    pass

# --- 5. Main Execution ---

# Importation de ta classe WSClient (Assure-toi que ce fichier est accessible)
# Si WSClient est dans le même fichier, supprime l'import.
try:
    from utils.WSClient import WSClient # Remplacer par le bon nom de fichier ou module
except ImportError:
    print("ERREUR: Impossible d'importer WSClient. Assure-toi que le fichier est là.")
    # Mock pour test si tu n'as pas le fichier sous la main
    class WSClient:
        def __init__(self, url, client_key, action_delegate, key_delegate, steps): pass
        async def run(self): 
            print("Simulation WS Client running... (Ctrl+C to stop)")
            while True: await asyncio.sleep(1)

if __name__ == "__main__":
    
    # 1. Séquence d'initialisation (Bloquante, avant de lancer l'async)
    try:
        init_lights_sequence()
    except Exception as e:
        print(f"Erreur DMX Init: {e}")

    # 2. Configuration du Client WS
    STEPS = {} # Ton objet steps si nécessaire
    client = WSClient(
        url="ws://192.168.10.182:8057/ws",
        client_key="atmosphere_light_activity",
        action_delegate=my_action_handler,
        key_delegate=my_key_handler,
        steps=STEPS
    )

    # 3. Lancement de la boucle asynchrone
    try:
        print("🚀 Lancement du client WebSocket...")
        asyncio.run(client.run())
    except KeyboardInterrupt:
        print("\nArrêt du programme.")
    finally:
        print("Fermeture propre du DMX.")
        dmx.blackout()
        time.sleep(0.1)
        dmx.stop()