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
from utils.WSClient import *

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
                case 1:
                    print("[+] Première réponse reçue du client.")
                    input(f"Appuyez sur Entrée pour continuer a l'etape {data['sequencing'] + 1}...")
                    # sequencing passe à 2
                    data["sequencing"] += 1
                    await ws_send_to(data.get("activity_atmosphere").get("ws_server_address"), data)

                    input(f"Appuyez sur Entrée pour continuer a l'etape {data['sequencing'] + 1}...")
                    
                    # sequencing passe à 3
                    data["sequencing"] += 1
                    await ws_send_to(data.get("activity_control").get("ws_server_address"), data)

                case 4:
                    print("[+] Quatrième réponse reçue du client.")
                    input(f"Appuyez sur Entrée pour continuer a l'etape {data['sequencing'] + 1}...")
                    # sequencing passe à 5
                    data["sequencing"] += 1
                    await ws_send_to(data.get("activity_atmosphere").get("ws_server_address"), data)
                    input(f"Appuyez sur Entrée pour continuer a l'etape {data['sequencing'] + 1}...")
                    # sequencing passe à 6
                    data["sequencing"] += 1
                    await ws_send_to(data.get("activity_monitoring").get("ws_server_address"), data)

                case 7:
                    print("[+] Septième réponse reçue du client.")
                    input(f"Appuyez sur Entrée pour continuer a l'etape {data['sequencing'] + 1}...")
                    # sequencing passe à 8
                    data["sequencing"] += 1
                    await ws_send_to(data.get("activity_atmosphere").get("ws_server_address"), data)
                    input(f"Appuyez sur Entrée pour continuer a l'etape {data['sequencing'] + 1}...")
                    # sequencing passe à 9
                    data["sequencing"] += 1
                    await ws_send_to(data.get("activity_oral").get("ws_server_address"), data)

                case 10:
                    print("[+] Dixième réponse reçue du client.")
                    input(f"Appuyez sur Entrée pour continuer a l'etape {data['sequencing'] + 1}...")
                    # sequencing passe à 11
                    data["sequencing"] += 1
                    await ws_send_to(data.get("activity_atmosphere").get("ws_server_address"), data)
                    input(f"Appuyez sur Entrée pour continuer a l'etape {data['sequencing'] + 1}...")
                    # sequencing passe à 12
                    data["sequencing"] += 1
                    await ws_send_to(data.get("activity_monitoring").get("ws_server_address"), data)

                case 13:
                    print("[+] Treizième réponse reçue du client.")
                    input(f"Appuyez sur Entrée pour continuer a l'etape {data['sequencing'] + 1}...")
                    # sequencing passe à 14
                    data["sequencing"] += 1
                    await ws_send_to(data.get("activity_atmosphere").get("ws_server_address"), data)
                    input(f"Appuyez sur Entrée pour continuer a l'etape {data['sequencing'] + 1}...")
                    # sequencing passe à 15
                    data["sequencing"] += 1
                    await ws_send_to(data.get("activity_knock_down").get("ws_server_address"), data)

                case 16:
                    print("[+] Quinzième réponse reçue du client.")
                    input(f"Appuyez sur Entrée pour continuer a l'etape {data['sequencing'] + 1}...")
                    # sequencing passe à 17
                    data["sequencing"] += 1
                    await ws_send_to(data.get("activity_atmosphere").get("ws_server_address"), data)
                    input(f"Appuyez sur Entrée pour continuer a l'etape {data['sequencing'] + 1}...")
                    # sequencing passe à 18
                    data["sequencing"] += 1
                    await ws_send_to(data.get("activity_monitoring").get("ws_server_address"), data)

                case 19:
                    print("[+] Dix-huitième réponse reçue du client.")
                    input(f"Appuyez sur Entrée pour continuer a l'etape {data['sequencing'] + 1}...")
                    # sequencing passe à 20
                    data["sequencing"] += 1
                    await ws_send_to(data.get("activity_atmosphere").get("ws_server_address"), data)
                    input(f"Appuyez sur Entrée pour continuer a l'etape {data['sequencing'] + 1}...")
                    # sequencing passe à 21
                    data["sequencing"] += 1
                    await ws_send_to(data.get("activity_speak_to_mom").get("ws_server_address"), data)

                case 22:
                    print("[+] Vingt-et-unième réponse reçue du client.")
                    input(f"Appuyez sur Entrée pour continuer a l'etape {data['sequencing'] + 1}...")
                    # sequencing passe à 23
                    data["sequencing"] += 1
                    await ws_send_to(data.get("activity_atmosphere").get("ws_server_address"), data)
                    input(f"Appuyez sur Entrée pour continuer a l'etape {data['sequencing'] + 1}...")
                    # sequencing passe à 24
                    data["sequencing"] += 1
                    await ws_send_to(data.get("activity_monitoring").get("ws_server_address"), data)
                case _:
                    print("[-] Ne corespond à aucune étape connue de sequencing.")

        

if __name__ == "__main__":
    config_path = os.path.join(parent_dir, "config.json")
    print(f"path du config: {config_path}")
    config_ws = {
        "host": "192.168.10.50",
        "port": 8005
    }
    server = AdvancedWSServer(delegate=WsDelegate(), config=config_ws)
    asyncio.run(server.start())
    try:
        while True:
            pass  # Keep the main thread alive
    except KeyboardInterrupt:
        server.stop()