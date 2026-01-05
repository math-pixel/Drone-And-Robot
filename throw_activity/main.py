import sys
import os
import numpy as np
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

from utils.WSClient import *
from utils.kinect.DephDetector import DepthDetector
import time

STEPS = [
        {
            "id": 1, 
            "actions": [
                {"id": 1, "type": "activity", "finished": False},
            ], 
            "authorized": False, 
            "finished": False
        },
    ]

class DepthDetectorDelegate:

    def __init__(self, wsClient = None):
        self.points = 0
        self.authorized = False
        self.maxPointsVictory = 20
        self.wsClient = wsClient
        self.action = None

    def start_detection(self, action: dict):
        self.action = action
        print(self.action)
        self.authorized = True
        print("Détection de profondeur démarrée.")
    
    def stop_detection(self):
        self.authorized = False
        print("Détection de profondeur arrêtée.")

    def add_points(self, pts):
        self.points += pts
        print(f"Points: {self.points}")

    def turn_rover(self):
        if self.points >= 0 and self.points <= 10:
            asyncio.run(self.wsClient.send_data({"key": "rover", "command": "turn_left", "angle": 15}))
            #turn rover  
        if self.points >= 50 and self.points <= 60:
            self.wsClient.send_data({"key": "rover", "command": "turn_left", "angle": 15})
            #turn rover  
        if self.points >= 80 and self.points <= 90:
            self.wsClient.send_data({"key": "rover", "command": "turn_left", "angle": 15})
            #turn rover        

    def process(self, grid_values):

        if self.authorized == False:
            return
        
        # Traiter les valeurs de la grille reçues du DepthDetector
        print("Grille de profondeur mise à jour:")
        print(grid_values)

        # Add points
        self.add_points(10)
        self.turn_rover()

        if self.points >= self.maxPointsVictory:
            print("Victoire atteinte!")
            self.stop_detection()
            self.action["finished"] = True
            asyncio.run(self.wsClient.send_action_finished("1", self.action["id"]))

        time.sleep(5)
        

if __name__ == "__main__":
    config_path = os.path.join(parent_dir, "config.json")

    depth_detector_delegate = DepthDetectorDelegate()
    depth_detector = DepthDetector(delegate=depth_detector_delegate)

    async def my_action_handler(action: dict, client: WSClient, step_id: int):
        """
        Delegate personnalisé pour gérer les actions.
        L'utilisateur implémente ici son match case.
        """
        action_id = action.get("id")
        action_type = action.get("type")
        
        print("message recu du serveur")
        print(action)
        if action_type == "activity":
            print("Autorisation de lancer la détection de profondeur.")
            depth_detector.delegate.start_detection(action = action)
            # Marquer comme terminé
            # action["finished"] = True
            # await client.send_action_finished(step_id, action_id)

    client = WSClient(
        url="ws://172.28.55.91:8057/ws",
        client_key="throw_activity",
        action_delegate=my_action_handler,
        steps=STEPS
    )
    depth_detector_delegate.wsClient = client
    depth_detector_delegate.loop = asyncio.get_event_loop()
    
    def run_detector_in_thread():
        print("📷 Démarrage du thread DepthDetector...")
        # Cette fonction est bloquante, c'est pourquoi on la met dans un thread
        depth_detector.run() 

    detector_thread = threading.Thread(target=run_detector_in_thread, daemon=True)
    detector_thread.start()
    
    asyncio.run(client.run())