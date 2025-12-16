import sys
import os
import threading

# --- BLOC MAGIQUE A METTRE TOUT EN HAUT ---

# 1. On prend le chemin du fichier actuel (server.py)
current_path = os.path.abspath(__file__)

# 2. On prend le dossier du fichier (serveur/)
current_dir = os.path.dirname(current_path)

# 3. On remonte d'un cran pour avoir le dossier racine (PROJET/)
parent_dir = os.path.dirname(current_dir)

# 4. On ajoute la racine aux chemins de Python
sys.path.append(parent_dir)

# ------------------------------------------

from utils.WSServer import *
from utils.WSClient import *
from utils.rpi.Bouton import *

# Création du bouton sur GPIO 17
btn = Bouton(pin=17, pull_up=True, long_press_time=2.0)

# === MÉTHODE 1: Avec callbacks ===
def quand_appuye():
    print("Bouton appuyé!")

def quand_relache(duree):
    print(f"Relâché après {duree:.2f}s")

def quand_long():
    print("Appui long détecté!")

def quand_double():
    print("Double-clic!")

btn.on_press = quand_appuye
btn.on_release = quand_relache
btn.on_long_press = quand_long
btn.on_double_click = quand_double

class WsDelegate(DelegateInterface):
    async def process(self, data, websocket):

        if not data:
            print("[-] Aucune donnée reçue.")
            return
        
        if data.get("name") != "global_data_transfer":
            print("[-] Données non pertinentes reçues.")
            response = {
                "status": "received",
                "original_data": data
            }
        else:
            print("[+] Données pertinentes reçues.")
            response = {
                "status": "processed",
                "original_data": data
            }
            await websocket.send(json.dumps(response))
            print("[+] Réponse envoyée au client.")

            match data.get("sequencing"):
                case 6:
                    print("[+] Sixième réponse reçue du client.")
                    input(f"Appuyez sur Entrée pour continuer a l'etape {data['sequencing'] + 1}...")
                    data["sequencing"] += 1
                    await ws_send_to(data.get("main_activity").get("ws_server_address"), data)
                case 12:
                    print("[+] Douzième réponse reçue du client.")
                    input(f"Appuyez sur Entrée pour continuer a l'etape {data['sequencing'] + 1}...")
                    data["sequencing"] += 1
                    await ws_send_to(data.get("main_activity").get("ws_server_address"), data)
                case 18:
                    print("[+] Dix-huitième réponse reçue du client.")
                    input(f"Appuyez sur Entrée pour continuer a l'etape {data['sequencing'] + 1}...")
                    data["sequencing"] += 1
                    await ws_send_to(data.get("main_activity").get("ws_server_address"), data)
                case 24:
                    print("[+] Vingt-quatrième réponse reçue du client.")
                    input(f"Appuyez sur Entrée pour terminer. ")
                case _:
                    print("[-] Ne corespond à aucune étape connue de sequencing.")

def run_server():
    result = asyncio.run(server.start())

if __name__ == "__main__":
    config_path = os.path.join(parent_dir, "config.json")
    print(f"path du config: {config_path}")
    config_ws = {
        "host": "192.168.10.103",
        "port": 8002
    }
    server = AdvancedWSServer(delegate=WsDelegate(), config=config_ws)
    thread1 = threading.Thread(target=run_server, daemon=True)
    thread1.start()
    
    print("[+] Serveur WebSocket démarré.")
    with open(config_path, 'r') as f:
        data = json.load(f)
    
    print("Appuyez sur le bouton...")
    btn.wait_for_press()

    asyncio.run(ws_send_to(data.get("main_activity").get("ws_server_address"), data))
    
    try:
        while True:
            pass  # Keep the main thread alive
    except KeyboardInterrupt:
        server.stop()

