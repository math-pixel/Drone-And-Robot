import sys
import os

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

class WsDelegate(DelegateInterface):
    async def process(self, data, websocket):
        response = {
            "status": "received",
            "original_data": data
        }
        await websocket.send(json.dumps(response))
        print("[+] Réponse envoyée au client.")

if __name__ == "__main__":
    server = AdvancedWSServer(delegate=WsDelegate(), config_file="./config.json")
    server.start()
    try:
        while True:
            pass  # Keep the main thread alive
    except KeyboardInterrupt:
        server.stop()