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

        # Charger la config UNE SEULE FOIS au démarrage
        self.config = self.load_config(config_path) if config_path else {}
        print("Config loaded:", self.config)
        self.audio_grid = self.config["grid_path_sound"]
        
        # Récupérer la grille de validation depuis la config
        self.grid_validation = self.get_grid_validation()
        
        # Initialiser avec la bonne taille basée sur la config
        grid_shape = self.grid_validation.shape if self.grid_validation is not None else (4, 4)
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
        """Ajoute un son à la queue ou le joue directement"""
        # Si aucun son ne joue, jouer directement
        if not self.player.is_any_playing():
            print(f"🔊 Joue directement: {sound_name} ({row}, {col})")
            self.player.play(sound_name)
        else:
            # Sinon, ajouter à la queue
            self.sound_queue.append((row, col, sound_name))
            print(f"📝 Ajouté à la queue: {sound_name} ({row}, {col})")

    def start_detection(self, action: dict):
        self.action = action
        print(self.action)
        self.authorized = True
        print("Détection de profondeur démarrée.")

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
        # Reset the grid when starting a new detection
        self.current_grid_completed = np.zeros((4, 4), dtype=int)  # Reset grid
        self.authorized = True
        print("Détection de profondeur démarrée.")

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

    def find_new_activated_index(self, new_grid):
        """
        Compare la grille actuelle (stockée) avec la nouvelle grille reçue.
        Retourne un tuple (row, col) si une nouvelle case est activée (0 -> 1).
        Sinon retourne None.
        """
        # Sécurité : si les dimensions ne correspondent pas, on ignore pour éviter un crash
        if self.current_grid_completed.shape != new_grid.shape:
            return None

        # Logique booléenne :
        # On cherche les cases où : (Nouvelle est True) ET (Ancienne est False)
        new_activations = (new_grid == 1) & (self.last_grid == 0)

        # np.argwhere renvoie une liste des coordonnées [row, col] où la condition est Vraie
        indices = np.argwhere(new_activations)

        if indices.size > 0:
            # On prend le premier index trouvé (même s'il y en a plusieurs)
            # On le convertit en tuple pour le retour (ex: (1, 2))
            return tuple(indices[0])
        
        return None

    def process(self, grid_values):
        # DEBUG : Afficher les grilles pour comprendre
        print(f"last_grid:\n{self.last_grid}")
        print(f"grid_values:\n{grid_values}")
        
        # 1. Chercher les nouvelles activations AVANT de mettre à jour last_grid
        new_index = self.find_new_activated_index(grid_values)

        if new_index is not None:
            print(f"!!! NOUVELLE ACTIVATION DÉTECTÉE À L'INDEX : {new_index} !!!")
            row, col = new_index
            if 0 <= row < len(self.audio_grid) and 0 <= col < len(self.audio_grid[row]):
                nom_son = self.audio_grid[row][col]
                self.queue_sound(row, col, str(nom_son))
        else:
            print("Pas de nouvelle activation")

        # 2. Mettre à jour last_grid APRÈS la comparaison
        self.last_grid = grid_values.copy()

        # 3. Mettre à jour current_grid_completed
        self.joinGrid(grid_values)
        
        if self.isActivityFinish():
            print("Envoie Activité terminée !")
            self.authorized = False
            asyncio.run(self.wsClient.send_action_finished("1", self.action["id"]))

if __name__ == "__main__":

    import pygame

    config_path = os.path.join(parent_dir, "./presentation_activity/config.json")
    depth_detector_delegate = DepthDetectorDelegate()
    depth_detector = DepthDetector(delegate=depth_detector_delegate)

    def run_detector_in_thread():
        print("📷 Démarrage du thread DepthDetector...")
        # Cette fonction est bloquante, c'est pourquoi on la met dans un thread
        depth_detector.run() 
        print("Trying to set reference depth...")
        if depth_detector.current_depth is not None:
            depth_detector.set_reference(depth_detector.current_depth) 
            print("✅ Reference depth set.")
        else: 
            print("No depth data available yet.")

    detector_thread = threading.Thread(target=run_detector_in_thread, daemon=True)
    detector_thread.start()
    
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
        url="ws://192.168.10.34:8057/ws",
        client_key="presentation_activity",
        action_delegate=my_action_handler,
        steps=STEPS
    )
    depth_detector_delegate.wsClient = client
    depth_detector_delegate.loop = asyncio.get_event_loop()

    async def main():
        while True:
            time.sleep(1)
    #asyncio.run(main())
    asyncio.run(client.run())