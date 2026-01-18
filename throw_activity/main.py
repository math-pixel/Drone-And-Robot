import sys
import os
import numpy as np
import threading
import asyncio

# --- BLOC MAGIQUE ---
current_path = os.path.abspath(__file__)
current_dir = os.path.dirname(current_path)
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)
# --------------------

from utils.WSClient import *
from utils.kinect.DephDetectorPolygone import DepthDetector
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

    def __init__(self, wsClient=None):
        self.points = 0
        self.authorized = False
        self.pointsToAdd = 10
        self.roverThresholdsTurn = [(0, 10), (50, 60), (80, 90)]
        self.maxPointsVictory = 100
        self.wsClient = wsClient
        self.action = None
        self.loop = None  # ⬅️ Référence à la boucle asyncio principale

    def _send_async(self, coro):
        """
        Envoie une coroutine de façon non-bloquante depuis un thread.
        """
        if self.loop is None:
            print("⚠️ Event loop non défini!")
            return None
        
        future = asyncio.run_coroutine_threadsafe(coro, self.loop)
        return future

    def _send_async_and_wait(self, coro, timeout=5):
        """
        Envoie une coroutine et attend le résultat (bloquant mais thread-safe).
        """
        if self.loop is None:
            print("⚠️ Event loop non défini!")
            return None
        
        future = asyncio.run_coroutine_threadsafe(coro, self.loop)
        try:
            return future.result(timeout=timeout)
        except Exception as e:
            print(f"❌ Erreur lors de l'envoi: {e}")
            return None

    def start_detection(self, action: dict):
        self.action = action
        print(self.action)
        self.authorized = True
        print("✅ Détection de profondeur démarrée.")
    
    def stop_detection(self):
        self.authorized = False
        print("🛑 Détection de profondeur arrêtée.")

    def add_points(self, pts):
        self.points += pts
        print(f"Points: {self.points}")
        self.set_score(self.points)
        
        # ✅ Utilise run_coroutine_threadsafe (NON bloquant)
        self._send_async(self.wsClient._send_json("update_jauge_score"))

    def turn_rover(self):
        """
        Tourne le rover à certains seuils de points.
        """
        thresholds = self.roverThresholdsTurn
        
        for low, high in thresholds:
            if low <= self.points <= high:
                # ✅ Planifie la séquence de rotation de façon non-bloquante
                self._send_async(self._rover_turn_sequence())
                break  # Une seule rotation par appel

    async def _rover_turn_sequence(self):
        """
        Séquence de rotation du rover (coroutine async).
        """
        await self.wsClient._send_json("rover_left_180")
        await asyncio.sleep(5)  # ⬅️ asyncio.sleep au lieu de time.sleep
        await self.wsClient._send_json("rover_right_180")

    def get_score(self):
        activity_list = self.wsClient.data.get("activity", [])
        for item in activity_list:
            if "throw_activity" in item:
                return item["throw_activity"].get("score", 0)
        return 0

    def set_score(self, score):
        activity_list = self.wsClient.data.get("activity", [])
        for item in activity_list:
            if "throw_activity" in item:
                item["throw_activity"]["score"] = score

    def process(self, grid_values):
        if not self.authorized:
            return
        
        print("📊 Grille de profondeur mise à jour:")
        print(grid_values)

        self.add_points(self.pointsToAdd)
        self.turn_rover()

        if self.points >= self.maxPointsVictory:
            print("🏆 Victoire atteinte!")
            self.stop_detection()
            self.action["finished"] = True
            self._send_async(
                self.wsClient.send_action_finished("1", self.action["id"])
            )


if __name__ == "__main__":
    config_path = os.path.join(parent_dir, "config.json")

    depth_detector_delegate = DepthDetectorDelegate()
    depth_detector = DepthDetector(delegate=depth_detector_delegate)

    async def my_action_handler(action: dict, client: WSClient, step_id: int):
        action_type = action.get("type")
        
        print("📨 Message reçu du serveur")
        print(action)
        
        if action_type == "activity":
            print("✅ Autorisation de lancer la détection de profondeur.")
            depth_detector.delegate.start_detection(action=action)

    async def my_connection_handler(client: WSClient, connected: bool):
        if connected:
            print("✅ Connecté au serveur WebSocket.")
            # ✅ Démarre la détection si une action a deja été reçue
            if depth_detector.delegate.action is not None:
                depth_detector.delegate.start_detection(
                    action=depth_detector.delegate.action
                )
        else:
            depth_detector.delegate.stop_detection()
            print("❌ Déconnecté du serveur WebSocket.")

    client = WSClient(
        url="ws://192.168.10.34:8057/ws",
        client_key="throw_activity",
        action_delegate=my_action_handler,
        connection_handler=my_connection_handler,
        steps=STEPS
    )
    
    depth_detector_delegate.wsClient = client

    def run_detector_in_thread():
        print("📷 Démarrage du thread DepthDetector...")
        depth_detector.run()
        asyncio.sleep(2)
        print("Trying to set reference depth...")
        if depth_detector.current_depth is not None:
            depth_detector.set_reference(depth_detector.current_depth) 
            print("✅ Reference depth set.")
        else: 
            print("No depth data available yet.")

    detector_thread = threading.Thread(target=run_detector_in_thread, daemon=True)
    detector_thread.start()

    # ✅ Récupère la boucle et la passe au delegate AVANT de la lancer
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    depth_detector_delegate.loop = loop
    
    # ✅ Lance le client sur cette boucle
    loop.run_until_complete(client.run())