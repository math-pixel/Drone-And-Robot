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
        self.roverThresholdsTurn = [(0, 10), (80, 90), (175,180)]
        self.voiceProfTurns = ["prof_heho", "prof_nrv", "prof_fin"]
        self.roverTurnedIndex = 0
        self.maxPointsVictory = 180
        self.wsClient = wsClient
        self.action = None
        self.loop = None  # ⬅️ Référence à la boucle asyncio principale
        self.finished_event = None
        self.last_score_time = 0   # Temps du dernier point marqué
        self.SCORE_COOLDOWN = 1.0  # Délai en secondes (ex: 1 seconde)

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
        self._send_async(self.wsClient._send_json("mom_activity_stepper_control_turn_right_10"))

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
        await self.wsClient._send_json(f"global_sound_{self.voiceProfTurns[self.roverTurnedIndex]}")
        self.roverTurnedIndex += 1
        await self.wsClient._send_json("rover_left_180")
        time.sleep(5)  # ⬅️ asyncio.sleep au lieu de time.sleep
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
        
        # 1. Vérifier si la grille contient au moins un "1" (Détection active)
        # (Si la grille est vide, on ne fait rien)
        if np.any(grid_values == 1):
            
            # 2. Vérifier le Cooldown (Non bloquant)
            current_time = time.time()
            if current_time - self.last_score_time > self.SCORE_COOLDOWN:
                
                print(f"🎯 Impact détecté ! (+{self.pointsToAdd} pts)")
                
                # A. Mettre à jour le temps
                self.last_score_time = current_time
                
                # B. Ajouter les points et gérer le rover
                self.add_points(self.pointsToAdd)

                if self.points >= 10 and self.points < 15:
                    self._send_async(self.wsClient._send_json("global_sound_ils_rigolent"))

                self.turn_rover()

                # C. Vérifier la victoire
                if self.points >= self.maxPointsVictory:
                    print("🏆 Victoire atteinte!")
                    self.stop_detection()
                    self.action["finished"] = True
                    
                    # 🔴 C'EST ICI QU'ON DÉBLOQUE LE HANDLER
                    if self.loop is not None and self.finished_event is not None:
                        print("🔓 Déblocage du signal de fin...")
                        self.loop.call_soon_threadsafe(self.finished_event.set)
                    else:
                        # Fallback si l'event n'est pas configuré (pour éviter que ça plante)
                        self._send_async(
                            self.wsClient.send_action_finished("1", self.action["id"])
                        )
            else:
                # Optionnel : Juste pour le debug, dire qu'on ignore
                # print("⏳ Cooldown actif, point ignoré...")
                pass


if __name__ == "__main__":
    config_path = os.path.join(parent_dir, "config.json")

    # 1. Création des objets
    depth_detector_delegate = DepthDetectorDelegate()
    depth_detector = DepthDetector(delegate=depth_detector_delegate)
    
    # 2. LIEN MAGIQUE (Pour que le delegate puisse prendre la ref)
    depth_detector_delegate.detector = depth_detector 

    # 3. Handlers WebSocket
    async def my_action_handler(action: dict, client: WSClient, step_id: int):
        print(f"📨 Action reçue: {action['type']}")
        
        if action["type"] == "activity":
            
            # 1. Créer le signal d'attente
            event = asyncio.Event()
            
            # 2. Le donner au delegate pour qu'il puisse l'activer plus tard
            depth_detector_delegate.finished_event = event
            
            # 3. Setup de la caméra (code existant)
            await asyncio.sleep(1)
            if depth_detector_delegate.detector and depth_detector_delegate.detector.current_depth is not None:
                depth_detector_delegate.detector.set_reference(depth_detector_delegate.detector.current_depth)
            
            # 4. Lancer le jeu
            depth_detector_delegate.start_detection(action=action)
            
            # 5. 🛑 BLOQUER ICI TANT QUE C'EST PAS FINI 🛑
            print(f"⏳ Jeu en cours... Attente des {depth_detector_delegate.maxPointsVictory} points...")
            await event.wait()
            
            print("🎉 Fin de l'attente, envoi de la confirmation au serveur.")
            # Le WSClient enverra le "step_finished" automatiquement après cette ligne

    async def my_connection_handler(client: WSClient, connected: bool):
        if connected:
            print("✅ Connecté au serveur WebSocket.")
        else:
            depth_detector_delegate.stop_detection()
            print("❌ Déconnecté.")

    # 4. Config Client
    client = WSClient(
        url="ws://192.168.10.123:8057/ws",
        client_key="throw_activity",
        action_delegate=my_action_handler,
        connection_handler=my_connection_handler,
        steps=STEPS
    )
    depth_detector_delegate.wsClient = client

    # 5. Démarrage du WebSocket dans un THREAD SÉPARÉ
    def run_websocket_thread():
        print("🌐 Démarrage du thread WebSocket...")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # On donne la loop au delegate pour qu'il puisse envoyer des messages plus tard
        depth_detector_delegate.loop = loop
        
        loop.run_until_complete(client.run())

    ws_thread = threading.Thread(target=run_websocket_thread, daemon=True)
    ws_thread.start()

    # 6. Démarrage de la Kinect dans le MAIN THREAD (Bloquant)
    print("📷 Démarrage de la Kinect (Main Thread)...")
    try:
        depth_detector.run()
    except KeyboardInterrupt:
        print("Arrêt demandé...")