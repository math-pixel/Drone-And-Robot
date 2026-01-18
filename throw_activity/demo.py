import sys
import os
import numpy as np
import threading
import time

# --- BLOC MAGIQUE ---
current_path = os.path.abspath(__file__)
current_dir = os.path.dirname(current_path)
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)
# --------------------

from utils.kinect.DephDetectorPolygone import DepthDetector


class DepthDetectorDelegate:

    def __init__(self):
        self.points = 0
        self.authorized = False
        self.pointsToAdd = 10
        self.roverThresholdsTurn = [(0, 10), (50, 60), (80, 90)]
        self.maxPointsVictory = 100
        self.action = None
        
        # Pour éviter de déclencher le rover plusieurs fois au même seuil
        self.triggered_thresholds = set()

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

    def reset_points(self):
        """Réinitialise les points et les seuils déclenchés"""
        self.points = 0
        self.triggered_thresholds.clear()
        print("🔄 Points réinitialisés à 0.")

    def add_points(self, pts):
        """Ajoute des points et affiche le score"""
        self.points += pts
        print(f"⭐ Points: {self.points} / {self.maxPointsVictory}")
        
        # Mode démo: pas d'envoi WebSocket, juste un affichage
        self._display_progress_bar()

    def _display_progress_bar(self):
        """Affiche une barre de progression dans la console"""
        progress = min(self.points / self.maxPointsVictory, 1.0)
        bar_length = 30
        filled = int(bar_length * progress)
        bar = "█" * filled + "░" * (bar_length - filled)
        percentage = int(progress * 100)
        print(f"   [{bar}] {percentage}%")

    def turn_rover(self):
        """
        Simule la rotation du rover à certains seuils de points.
        En mode démo: affiche juste des messages.
        """
        thresholds = self.roverThresholdsTurn
        
        for low, high in thresholds:
            threshold_key = (low, high)
            
            # Vérifie si on est dans le seuil ET qu'on ne l'a pas déjà déclenché
            if low <= self.points <= high and threshold_key not in self.triggered_thresholds:
                self.triggered_thresholds.add(threshold_key)
                
                # Mode démo: simulation du rover
                print(f"🤖 [ROVER SIMULATION] Rotation gauche 180°")
                print(f"   ⏳ Attente 5 secondes...")
                # Note: En mode démo, on ne bloque pas vraiment 5 secondes
                print(f"🤖 [ROVER SIMULATION] Rotation droite 180°")
                break

    def get_score(self):
        """Retourne le score actuel"""
        return self.points

    def set_score(self, score):
        """Définit le score"""
        self.points = score

    def process(self, grid_values):
        """Traite les valeurs de la grille de profondeur"""
        if not self.authorized:
            return
        
        print("📊 Grille de profondeur mise à jour:")
        print(grid_values)

        # Ajouter des points
        self.add_points(self.pointsToAdd)
        
        # Vérifier si on doit tourner le rover
        self.turn_rover()

        # Vérifier la victoire
        if self.points >= self.maxPointsVictory:
            print("\n" + "="*50)
            print("🏆🎉 VICTOIRE ATTEINTE ! 🎉🏆")
            print("="*50 + "\n")
            self.stop_detection()


# ============================================
# MAIN - MODE DEMO
# ============================================

if __name__ == "__main__":
    import pygame

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
    
    # Créer une fenêtre pour capturer les événements
    screen = pygame.display.set_mode((450, 280))
    pygame.display.set_caption("Mode Démo - Throw Activity")
    
    # Polices pour afficher le statut
    font = pygame.font.Font(None, 36)
    small_font = pygame.font.Font(None, 24)
    large_font = pygame.font.Font(None, 48)

    def draw_status():
        """Dessine le statut actuel sur la fenêtre"""
        screen.fill((30, 30, 30))  # Fond gris foncé
        
        # Titre
        title = font.render("Mode Démo - Throw Activity", True, (255, 255, 255))
        screen.blit(title, (20, 15))
        
        # Score avec grande police
        score_text = f"{depth_detector_delegate.points} / {depth_detector_delegate.maxPointsVictory}"
        score_color = (0, 255, 0) if depth_detector_delegate.points >= depth_detector_delegate.maxPointsVictory else (255, 255, 0)
        score = large_font.render(score_text, True, score_color)
        screen.blit(score, (20, 50))
        
        # Barre de progression
        progress = min(depth_detector_delegate.points / depth_detector_delegate.maxPointsVictory, 1.0)
        bar_width = 400
        bar_height = 20
        bar_x = 20
        bar_y = 95
        
        # Fond de la barre
        pygame.draw.rect(screen, (60, 60, 60), (bar_x, bar_y, bar_width, bar_height))
        # Progression
        fill_color = (0, 200, 0) if progress < 1.0 else (255, 215, 0)  # Or si victoire
        pygame.draw.rect(screen, fill_color, (bar_x, bar_y, int(bar_width * progress), bar_height))
        # Bordure
        pygame.draw.rect(screen, (100, 100, 100), (bar_x, bar_y, bar_width, bar_height), 2)
        
        # Statut de la détection
        status_color = (0, 255, 0) if depth_detector_delegate.authorized else (255, 0, 0)
        status_text = "ACTIVÉ" if depth_detector_delegate.authorized else "DÉSACTIVÉ"
        status = small_font.render(f"Détection: {status_text}", True, status_color)
        screen.blit(status, (20, 130))
        
        # Statut de la référence
        ref_set = depth_detector.reference_depth is not None
        ref_color = (0, 255, 0) if ref_set else (255, 165, 0)
        ref_text = "Définie" if ref_set else "Non définie"
        ref_status = small_font.render(f"Référence: {ref_text}", True, ref_color)
        screen.blit(ref_status, (220, 130))
        
        # Seuils rover déclenchés
        triggered = len(depth_detector_delegate.triggered_thresholds)
        total = len(depth_detector_delegate.roverThresholdsTurn)
        rover_text = small_font.render(f"Rover triggers: {triggered}/{total}", True, (150, 150, 255))
        screen.blit(rover_text, (20, 155))
        
        # Instructions
        instructions = [
            "[P] Toggle détection ON/OFF",
            "[R] Définir référence de profondeur",
            "[C] Réinitialiser les points",
            "[Q/ESC] Quitter"
        ]
        
        y_offset = 190
        for instruction in instructions:
            text = small_font.render(instruction, True, (200, 200, 200))
            screen.blit(text, (20, y_offset))
            y_offset += 22
        
        pygame.display.flip()

    print("\n" + "="*50)
    print("🎮 MODE DEMO - THROW ACTIVITY")
    print("="*50)
    print("[P] - Activer/Désactiver la détection")
    print("[R] - Définir la référence de profondeur")
    print("[C] - Réinitialiser les points")
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
                
                # Touche C - Reset les points
                elif event.key == pygame.K_c:
                    depth_detector_delegate.reset_points()
                
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