import sys
import os
import numpy as np
import threading
import asyncio
import time
from collections import deque

# --- BLOC MAGIQUE A METTRE TOUT EN HAUT ---

# 1. On prend le chemin du fichier actuel (server.py)
current_path = os.path.abspath(__file__)

# 2. On prend le dossier du fichier (serveur/)
current_dir = os.path.dirname(current_path)

# 3. On remonte d'un cran pour avoir le dossier racine (PROJET/)
parent_dir = os.path.dirname(current_dir)

AUDIO_MOTS_EXPOSE = "audios\mots_expose\\"
EXT_AUDIO = ".wav"

# 4. On ajoute la racine aux chemins de Python
sys.path.append(parent_dir)

# ------------------------------------------

from utils.WSClient import *
from utils.kinect.DephDetectorPolygone import DepthDetector
from utils.AudioPlayer import AudioPlayer


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

    def __init__(self, audio_grid=None, wsClient=None):
        self.player = AudioPlayer()
        self.wsClient = wsClient
        self.authorized = False
        self.action = None

        self.finished_event = None
        self.loop = None

        # Charger la config UNE SEULE FOIS au démarrage
        self.config = self.load_config(config_path) if config_path else {}
        print("Config loaded:", self.config)
        self.audio_grid = self.config["grid_path_sound"]
        
        # Récupérer la grille de validation depuis la config
        self.grid_validation = self.get_grid_validation()
        
        # Initialiser avec la bonne taille basée sur la config
        grid_shape = self.grid_validation.shape if self.grid_validation is not None else (5, 5)
        self.current_grid_completed = np.zeros(grid_shape, dtype=int)

        self.last_grid = np.zeros(grid_shape, dtype=int)
        
        # Load multiple sounds at once
        for row in range(len(self.audio_grid)):
            for col in range(len(self.audio_grid[row])):
                nom_fichier = self.audio_grid[row][col] + EXT_AUDIO
                # os.path.join s'occupe de mettre les séparateurs entre les dossiers
                chemin_complet = os.path.join(parent_dir, AUDIO_MOTS_EXPOSE, nom_fichier)

                print(f"Loading sound for cell ({row}, {col}): {chemin_complet}")
                self.player.load(self.audio_grid[row][col], chemin_complet)
                
                # self.audio_grid[row][col] = AUDIO_MOTS_EXPOSE + self.audio_grid[row][col] + EXT_AUDIO
        # self.player.load_multiple({
        #     "0": "music.wav",
        #     "1": "explosion.wav",
        #     "2": "jump.wav"
        # })
        
        # NOUVEAU : Système de queue audio
        self.sound_queue = deque()  # Queue de tuples (row, col, sound_name)
    
        # Configurer la callback
        self.player.set_on_finished_callback(self._on_sound_finished)

        self.last_activation_times = np.zeros(grid_shape, dtype=float)
        self.COOLDOWN_DELAY = 5 

    def _on_sound_finished(self, finished_sound_name):
        """Callback appelée quand un son est terminé"""
        print(f"✅ Son terminé: {finished_sound_name}")
        self._play_next_in_queue()

    def _play_next_in_queue(self):
        """Joue le prochain son valide de la queue"""
        while self.sound_queue:
            row, col, sound_name = self.sound_queue.popleft()
            
            # Vérifier si la cellule est TOUJOURS active
            if row < self.last_grid.shape[0] and col < self.last_grid.shape[1]:
                if self.last_grid[row, col] == 1:
                    # Cellule encore active → Jouer le son
                    print(f"🔊 Joue depuis queue: {sound_name} ({row}, {col})")
                    self.player.play(sound_name)
                    return
                else:
                    # Cellule inactive → Ignorer
                    print(f"⏭️ Ignoré (cellule inactive): {sound_name} ({row}, {col})")
        
        print("📭 Queue audio vide")

    def queue_sound(self, row, col, sound_name):
        """Ajoute un son à la queue ou le joue directement (AVEC ANTI-SPAM)"""
        
        # ANTI-SPAM : Vérifier si ce son exact est déjà dans la file d'attente
        for item in self.sound_queue:
            if item == (row, col, sound_name):
                print(f"🚫 Doublon ignoré pour la queue : {sound_name}")
                return

        # Si aucun son ne joue, jouer directement
        if not self.player.is_any_playing():
            print(f"🔊 Joue directement: {sound_name} ({row}, {col})")
            self.player.play(sound_name)
        else:
            # Sinon, ajouter à la queue
            self.sound_queue.append((row, col, sound_name))
            print(f"📝 Ajouté à la queue: {sound_name} ({row}, {col})")

    def load_config(self, config_path):
        """Charge la config depuis un fichier JSON"""
        import json
        try:
            full_path = os.path.join(parent_dir, config_path)
            with open(full_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"⚠️ Config file not found: {config_path}")
            return {}
        except json.JSONDecodeError:
            print(f"⚠️ Invalid JSON in: {config_path}")
            return {}

    def get_grid_validation(self):
        """Récupère la grille de validation depuis la config chargée"""
        try:
            grid = self.config["depth_detector"]["grid_validation"]
            return np.array(grid)
        except KeyError as e:
            print(f"⚠️ Missing config key: {e}")
            print("Using default 4x4 grid validation")
            # Grille par défaut si la config est manquante
            return np.array([
                [0, 1, 1, 0, 0],
                [0, 0, 1, 0, 0],
                [0, 1, 1, 0, 1],
                [0, 1, 1, 1, 1],
                [0, 0, 1, 1, 0]
            ])

    def start_detection(self, action: dict):
        self.action = action
        print(self.action)
        self.authorized = True
        print("Détection de profondeur démarrée.")

    def stop_detection(self):
        self.authorized = False
        print("Détection de profondeur arrêtée.")

    def joinGrid(self, grid_values):
        # Validate incoming grid
        if grid_values is None or grid_values.size == 0:
            print("Warning: Empty grid received, skipping...")
            return
        
        # Ensure shapes match (reset if needed)
        if self.current_grid_completed.shape != grid_values.shape:
            print(f"Resizing grid from {self.current_grid_completed.shape} to {grid_values.shape}")
            self.current_grid_completed = np.zeros(grid_values.shape, dtype=int)
        
        # Conversion en arrays numpy et OR logique
        self.current_grid_completed = np.logical_or(
            self.current_grid_completed, 
            grid_values
        ).astype(int)
   
    def isActivityFinish(self) -> bool:
        """Vérifie si l'activité est terminée - utilise la config déjà chargée"""
        if self.grid_validation is None:
            return False
        
        # Vérifie que les shapes correspondent
        if self.current_grid_completed.shape != self.grid_validation.shape:
            print(f"⚠️ Shape mismatch: {self.current_grid_completed.shape} vs {self.grid_validation.shape}")
            return False

        # print("Vérification de la complétion de la grille...")
        # print(self.current_grid_completed   )
        
        return np.all(self.current_grid_completed >= self.grid_validation)
        
    def playSound(self, grid_values_data):
        for row in range(grid_values_data.shape[0]):
            for col in range(grid_values_data.shape[1]):
                if grid_values_data[row, col] == 1:
                    self.player.play(str(self.audio_grid[row][col]))
                    print(f"Jouer le son pour la cellule ({row}, {col})")

    def find_new_activated_indices(self, new_grid):
        """
        Retourne TOUS les index qui viennent de passer à 1.
        """
        if self.current_grid_completed.shape != new_grid.shape:
            return []

        # Logique : (Nouveau est 1) ET (Ancien est 0)
        new_activations = (new_grid == 1) & (self.last_grid == 0)
        
        # Retourne une liste de tuples [(row, col), (row, col)...]
        indices = np.argwhere(new_activations)
        return [tuple(idx) for idx in indices]

    def process(self, grid_values):
        if not self.authorized:
            return

        if grid_values is None:
            return
        
        # 1. Chercher TOUTES les nouvelles activations (avec la méthode corrigée précédente)
        # Note: Assure-toi d'avoir implémenté la méthode find_new_activated_indices 
        # qui retourne une liste, comme vu dans la réponse précédente.
        new_indices = self.find_new_activated_indices(grid_values)
        
        current_time = time.time() # Heure actuelle

        for (row, col) in new_indices:
            
            # --- LE COOLDOWN CHECK EST ICI ---
            last_time = self.last_activation_times[row, col]
            
            if current_time - last_time < self.COOLDOWN_DELAY:
                print(f"⏳ Cooldown actif pour ({row}, {col}), ignoré.")
                continue # On passe au suivant sans jouer le son
            
            # Si on est ici, c'est que le délai est passé
            print(f"!!! NOUVELLE ACTIVATION VALIDÉE : ({row}, {col}) !!!")
            
            if 0 <= row < len(self.audio_grid) and 0 <= col < len(self.audio_grid[row]):
                nom_son = self.audio_grid[row][col]
                
                # On met à jour le temps pour cette case
                self.last_activation_times[row, col] = current_time
                
                # On lance le son
                self.queue_sound(row, col, str(nom_son))

        # 2. Mettre à jour last_grid APRÈS avoir tout traité
        self.last_grid = grid_values.copy()

        # 3. Mettre à jour current_grid_completed
        self.joinGrid(grid_values)
                
        if self.isActivityFinish():
            print("Grille complétée détectée !")
            self.authorized = False
            
            # MODIFICATION ICI :
            # Au lieu de lancer asyncio.run(), on signale à la boucle principale que c'est fini
            if self.loop is not None and self.finished_event is not None:
                print("Signal envoyé au thread principal...")
                self.loop.call_soon_threadsafe(self.finished_event.set)
            else:
                print("ERREUR : Impossible de signaler la fin (Loop ou Event manquant)")

if __name__ == "__main__":
    import pygame
    
    # 1. Initialisation
    pygame.init() # Important si vous utilisez le mixeur audio
    
    config_path = os.path.join(parent_dir, "./presentation_activity/config.json")
    depth_detector_delegate = DepthDetectorDelegate()
    depth_detector = DepthDetector(delegate=depth_detector_delegate)

    # 2. Définition des Handlers
    async def my_action_handler(action: dict, client: WSClient, step_id: int):
        print(f"📩 Action reçue: {action['type']}")
        
        if action["type"] == "activity":
            # A. SETUP SYNCHRO
            loop = asyncio.get_running_loop()
            event = asyncio.Event()
            depth_detector.delegate.loop = loop
            depth_detector.delegate.finished_event = event

            # B. REFERENCE KINECT (On prend la ref maintenant)
            print("📷 Prise de référence Kinect...")
            # On attend un peu pour être sûr que la caméra a une image
            await asyncio.sleep(1) 
            
            if depth_detector.current_depth is not None:
                depth_detector.set_reference(depth_detector.current_depth)
                print("✅ Référence définie !")
            else:
                print("⚠️ Pas de profondeur reçue (la fenêtre s'ouvre-t-elle ?)")

            # C. START
            depth_detector.delegate.start_detection(action=action)
            
            print("⏳ En attente du joueur...")
            await event.wait()
            
            print("🎉 Terminé !")
            await client.send_action_finished(str(step_id), action["id"])

    async def my_connection_handler(client: WSClient, connected: bool):
        if connected:
            print("✅ WebSocket Connecté.")
        else:
            print("❌ WebSocket Déconnecté.")
            depth_detector.delegate.stop_detection()

    # 3. Création du Client
    client = WSClient(
        url="ws://192.168.10.123:8057/ws",
        client_key="presentation_activity",
        action_delegate=my_action_handler,
        connection_handler=my_connection_handler,
        steps=STEPS
    )
    depth_detector_delegate.wsClient = client

    # --- LE GRAND CHANGEMENT EST ICI ---

    # 4. On lance le WebSocket dans un Thread SÉPARÉ
    def run_websocket_thread():
        print("🌐 Démarrage du thread WebSocket...")
        # On crée une nouvelle boucle pour ce thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(client.run())

    ws_thread = threading.Thread(target=run_websocket_thread, daemon=True)
    ws_thread.start()

    # 5. On lance la Kinect dans le MAIN THREAD (Bloquant)
    # C'est nécessaire pour que cv2.imshow ou pygame.display fonctionnent
    print("📷 Démarrage de la Kinect (Main Thread)...")
    try:
        depth_detector.run()
    except KeyboardInterrupt:
        print("Arrêt demandé...")
    
    # Quand on ferme la fenêtre Kinect, le script s'arrête
    print("Fin du programme.")