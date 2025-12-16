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
                case 2:
                    print(f"Mise à jour de l'atmosphère. Passage à l'étape {data['sequencing'] + 1}.")
                    data["sequencing"] += 1
                case 5:
                    print(f"Mise à jour de l'atmosphère. Passage à l'étape {data['sequencing'] + 1}.")
                    data["sequencing"] += 1
                case 8:
                    print(f"Mise à jour de l'atmosphère. Passage à l'étape {data['sequencing'] + 1}.")
                    data["sequencing"] += 1
                case 11:
                    print(f"Mise à jour de l'atmosphère. Passage à l'étape {data['sequencing'] + 1}.")
                    data["sequencing"] += 1
                case 14:
                    print(f"Mise à jour de l'atmosphère. Passage à l'étape {data['sequencing'] + 1}.")
                    data["sequencing"] += 1
                case 17:
                    print(f"Mise à jour de l'atmosphère. Passage à l'étape {data['sequencing'] + 1}.")
                    data["sequencing"] += 1
                case 20:
                    print(f"Mise à jour de l'atmosphère. Passage à l'étape {data['sequencing'] + 1}.")
                    data["sequencing"] += 1
                case 23:
                    print(f"Mise à jour de l'atmosphère. Passage à l'étape {data['sequencing'] + 1}.")
                    data["sequencing"] += 1
                case _:
                    print("[-] Ne corespond à aucune étape connue de sequencing.")

if __name__ == "__main__":
    config_path = os.path.join(parent_dir, "config.json")
    print(f"path du config: {config_path}")
    config_ws = {
        "host": "192.168.10.182",
        "port": 8001
    }
    server = AdvancedWSServer(delegate=WsDelegate(), config=config_ws)
    asyncio.run(server.start())
    try:
        while True:
            pass  # Keep the main thread alive
    except KeyboardInterrupt:
        server.stop()