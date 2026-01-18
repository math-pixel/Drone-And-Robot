import sys
import os
import numpy as np
import threading
import time
from collections import deque

# --- BLOC MAGIQUE A METTRE TOUT EN HAUT ---
current_path = os.path.abspath(__file__)
current_dir = os.path.dirname(current_path)
parent_dir = os.path.dirname(current_dir)

AUDIO_MOTS_EXPOSE = "audios\\mots_expose\\"
EXT_AUDIO = ".wav"

sys.path.append(parent_dir)
# ------------------------------------------

from utils.kinect.DephDetectorPolygone import DepthDetector
from utils.AudioPlayer import AudioPlayer

# Pas de STEPS nécessaire en mode démo


class DepthDetectorDelegate:

    def __init__(self, audio_grid=None):
        self.player = AudioPlayer()
        self.authorized = False
        self.action = None

        # Charger la config UNE SEULE FOIS au démarrage
        self.config = self.load_config(config_path) if config_path else {}
        print("Config loaded:", self.config)
        self.audio_grid = self.config.get("grid_path_sound", [])
        
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
                chemin_complet = os.path.join(parent_dir, AUDIO_MOTS_EXPOSE, nom_fichier)
                print(f"Loading sound for cell ({row}, {col}): {chemin_complet}")
                self.player.load(self.audio_grid[row][col], chemin_complet)
        
        # Système de queue audio
        self.sound_queue = deque()
        self.player.set_on_finished_callback(self._on_sound_finished)

    def _on_sound_finished(self, finished_sound_name):
        """Callback appelée quand un son est terminé"""
        print(f"✅ Son terminé: {finished_sound_name}")
        self._play_next_in_queue()

    def _play_next_in_queue(self):
        """Joue le prochain son valide de la queue"""
        while self.sound_queue:
            row, col, sound_name = self.sound_queue.popleft()
            
            if row < self.last_grid.shape[0] and col < self.last_grid.shape[1]:
                if self.last_grid[row, col] == 1:
                    print(f"🔊 Joue depuis queue: {sound_name} ({row}, {col})")
                    self.player.play(sound_name)
                    return
                else:
                    print(f"⏭️ Ignoré (cellule inactive): {sound_name} ({row}, {col})")
        
        print("📭 Queue audio vide")

    def queue_sound(self, row, col, sound_name):
        """Ajoute un son à la queue ou le joue directement"""
        if not self.player.is_any_playing():
            print(f"🔊 Joue directement: {sound_name} ({row}, {col})")
            self.player.play(sound_name)
        else:
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
            print("Using default 5x5 grid validation")
            return np.array([
                [0, 1, 1, 0, 0],
                [0, 0, 1, 0, 0],
                [0, 1, 1, 0, 1],
                [0, 1, 1, 1, 1],
                [0, 0, 1, 1, 0]
            ])

    def start_detection(self):
        """Démarre la détection (mode démo - sans action)"""
        self.authorized = True
        print("✅ Détection de profondeur ACTIVÉE.")

    def stop_detection(self):
        """Arrête la détection"""
        self.authorized = False
        print("🛑 Détection de profondeur DÉSACTIVÉE.")

    def toggle_detection(self):
        """Bascule l'état de la détection"""
        if self.authorized:
            self.stop_detection()
        else:
            self.start_detection()

    def reset_grids(self):
        """Réinitialise les grilles de suivi"""
        grid_shape = self.grid_validation.shape if self.grid_validation is not None else (4, 4)
        self.current_grid_completed = np.zeros(grid_shape, dtype=int)
        self.last_grid = np.zeros(grid_shape, dtype=int)
        print("🔄 Grilles réinitialisées.")

    def joinGrid(self, grid_values):
        if grid_values is None or grid_values.size == 0:
            print("Warning: Empty grid received, skipping...")
            return
        
        if self.current_grid_completed.shape != grid_values.shape:
            print(f"Resizing grid from {self.current_grid_completed.shape} to {grid_values.shape}")
            self.current_grid_completed = np.zeros(grid_values.shape, dtype=int)
        
        self.current_grid_completed = np.logical_or(
            self.current_grid_completed, 
            grid_values
        ).astype(int)
   
    def isActivityFinish(self) -> bool:
        """Vérifie si l'activité est terminée"""
        if self.grid_validation is None:
            return False
        
        if self.current_grid_completed.shape != self.grid_validation.shape:
            print(f"⚠️ Shape mismatch: {self.current_grid_completed.shape} vs {self.grid_validation.shape}")
            return False
        
        return np.all(self.current_grid_completed >= self.grid_validation)

    def find_new_activated_index(self, new_grid):
        """
        Compare la grille actuelle avec la nouvelle grille reçue.
        Retourne un tuple (row, col) si une nouvelle case est activée.
        """
        if self.current_grid_completed.shape != new_grid.shape:
            return None

        new_activations = (new_grid == 1) & (self.last_grid == 0)
        indices = np.argwhere(new_activations)

        if indices.size > 0:
            return tuple(indices[0])
        
        return None

    def process(self, grid_values):
        if not self.authorized:
            return

        # DEBUG
        print(f"last_grid:\n{self.last_grid}")
        print(f"grid_values:\n{grid_values}")
        
        # 1. Chercher les nouvelles activations
        new_index = self.find_new_activated_index(grid_values)

        if new_index is not None:
            print(f"!!! NOUVELLE ACTIVATION DÉTECTÉE À L'INDEX : {new_index} !!!")
            row, col = new_index
            if 0 <= row < len(self.audio_grid) and 0 <= col < len(self.audio_grid[row]):
                nom_son = self.audio_grid[row][col]
                self.queue_sound(row, col, str(nom_son))
        else:
            print("Pas de nouvelle activation")

        # 2. Mettre à jour last_grid
        self.last_grid = grid_values.copy()

        # 3. Mettre à jour current_grid_completed
        self.joinGrid(grid_values)
        
        # 4. Vérifier si terminé (mode démo: juste un message)
        if self.isActivityFinish():
            print("🏆 ACTIVITÉ TERMINÉE ! 🏆")
            self.authorized = False


# ============================================
# MAIN - MODE DEMO
# ============================================

if __name__ == "__main__":
    import pygame

    # Chemin de config
    config_path = "./presentation_activity/config.json"

    # Créer le delegate et le detector
    depth_detector_delegate = DepthDetectorDelegate()
    depth_detector = DepthDetector(delegate=depth_detector_delegate)

    def run_detector_in_thread():
        """Thread pour le DepthDetector (bloquant)"""
        print("📷 Démarrage du thread DepthDetector...")
        depth_detector.run()

    # Démarrer le thread du detector
    detector_thread = threading.Thread(target=run_detector_in_thread, daemon=True)
    detector_thread.start()

    # Initialiser pygame pour les entrées clavier
    pygame.init()
    
    # Créer une petite fenêtre pour capturer les événements
    screen = pygame.display.set_mode((400, 200))
    pygame.display.set_caption("Mode Démo - Kinect Depth Detector")
    
    # Police pour afficher le statut
    font = pygame.font.Font(None, 36)
    small_font = pygame.font.Font(None, 24)

    def draw_status():
        """Dessine le statut actuel sur la fenêtre"""
        screen.fill((30, 30, 30))  # Fond gris foncé
        
        # Titre
        title = font.render("Mode Démo - Contrôles", True, (255, 255, 255))
        screen.blit(title, (20, 20))
        
        # Statut de la détection
        status_color = (0, 255, 0) if depth_detector_delegate.authorized else (255, 0, 0)
        status_text = "ACTIVÉ" if depth_detector_delegate.authorized else "DÉSACTIVÉ"
        status = small_font.render(f"Détection: {status_text}", True, status_color)
        screen.blit(status, (20, 60))
        
        # Statut de la référence
        ref_set = depth_detector.reference_depth is not None
        ref_color = (0, 255, 0) if ref_set else (255, 165, 0)
        ref_text = "Définie" if ref_set else "Non définie"
        ref_status = small_font.render(f"Référence: {ref_text}", True, ref_color)
        screen.blit(ref_status, (20, 90))
        
        # Instructions
        instructions = [
            "[P] Toggle détection ON/OFF",
            "[R] Définir référence de profondeur",
            "[C] Réinitialiser les grilles",
            "[Q/ESC] Quitter"
        ]
        
        y_offset = 130
        for instruction in instructions:
            text = small_font.render(instruction, True, (200, 200, 200))
            screen.blit(text, (20, y_offset))
            y_offset += 20
        
        pygame.display.flip()

    print("\n" + "="*50)
    print("🎮 MODE DEMO - CONTRÔLES CLAVIER")
    print("="*50)
    print("[P] - Activer/Désactiver la détection")
    print("[R] - Définir la référence de profondeur")
    print("[C] - Réinitialiser les grilles")
    print("[Q] ou [ESC] - Quitter")
    print("="*50 + "\n")

    # Boucle principale
    running = True
    clock = pygame.time.Clock()

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            
            elif event.type == pygame.KEYDOWN:
                # Touche P - Toggle détection
                if event.key == pygame.K_p:
                    depth_detector_delegate.toggle_detection()
                
                # Touche R - Définir la référence
                elif event.key == pygame.K_r:
                    print("🎯 Tentative de définition de la référence...")
                    if depth_detector.current_depth is not None:
                        depth_detector.set_reference(depth_detector.current_depth)
                        print("✅ Référence de profondeur définie!")
                    else:
                        print("⚠️ Pas de données de profondeur disponibles.")
                
                # Touche C - Reset les grilles
                elif event.key == pygame.K_c:
                    depth_detector_delegate.reset_grids()
                
                # Touche Q ou ESC - Quitter
                elif event.key == pygame.K_q or event.key == pygame.K_ESCAPE:
                    print("👋 Fermeture du mode démo...")
                    running = False

        # Dessiner le statut
        draw_status()
        
        # Limiter à 30 FPS
        clock.tick(30)

    # Nettoyage
    pygame.quit()
    print("✅ Mode démo terminé.")