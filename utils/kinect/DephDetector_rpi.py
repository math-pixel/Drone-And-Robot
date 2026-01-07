#!/usr/bin/env python3
"""
DepthDetector pour Raspberry Pi 4 + Kinect v2
Toutes les fonctionnalités de la version Windows conservées
"""

import subprocess
import numpy as np
import cv2
import json
import os
import threading
import time

# Fichier de configuration
CONFIG_FILE = "grid_config.json"


class DepthDetector:
    def __init__(self, delegate=None):
        # Valeurs par défaut
        self.default_config = {
            # Position de la grille
            "start_x": 50,
            "start_y": 50,
            
            # Dimensions de la grille
            "cols": 5,
            "rows": 4,
            "cell_w": 80,
            "cell_h": 70,
            
            # Détection
            "threshold": 10,          # Seuil en mm (1cm = 10mm)
            
            # Couleurs (BGR)
            "color_background": [255, 100, 0],    # Bleu pour le fond
            "color_object": [0, 0, 255],          # Rouge pour les objets
            "color_grid": [0, 255, 0],            # Vert pour la grille
            "color_text": [255, 255, 255],        # Blanc pour le texte
            "show_graph": True
        }
        
        # Charger la configuration
        self.load_config()
        
        # === RÉFÉRENCE DE PROFONDEUR ===
        self.reference_depth = None
        self.reference_set = False
        
        # === ÉTAT DE LA GRILLE ===
        self.grid_values = None
        self.delegate = delegate
        
        # === KINECT (subprocess) ===
        self.process = None
        self.running = False
        self.current_depth = None
        self.frame_width = 512
        self.frame_height = 424
        self.subsample = 4  # Correspondant au C++
        
        # Chemin vers l'exécutable C++
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.capture_bin = os.path.join(current_dir, "depth_capture")
        
        print("✅ DepthDetector initialisé (mode Raspberry Pi)")
    
    # ========================
    # CONFIGURATION
    # ========================
    
    def load_config(self):
        """Charge la configuration depuis le fichier JSON"""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                print(f"✅ Configuration chargée depuis {CONFIG_FILE}")
                self.apply_config(config)
            except Exception as e:
                print(f"⚠️ Erreur de lecture du JSON: {e}")
                self.apply_default_config()
        else:
            print(f"ℹ️ Pas de fichier {CONFIG_FILE}, utilisation des valeurs par défaut")
            self.apply_default_config()
    
    def apply_config(self, config):
        """Applique une configuration"""
        self.start_x = config.get("start_x", self.default_config["start_x"])
        self.start_y = config.get("start_y", self.default_config["start_y"])
        self.cols = config.get("cols", self.default_config["cols"])
        self.rows = config.get("rows", self.default_config["rows"])
        self.cell_w = config.get("cell_w", self.default_config["cell_w"])
        self.cell_h = config.get("cell_h", self.default_config["cell_h"])
        self.threshold = config.get("threshold", self.default_config["threshold"])
        self.color_background = tuple(config.get("color_background", self.default_config["color_background"]))
        self.color_object = tuple(config.get("color_object", self.default_config["color_object"]))
        self.color_grid = tuple(config.get("color_grid", self.default_config["color_grid"]))
        self.color_text = tuple(config.get("color_text", self.default_config["color_text"]))
        self.show_graph = config.get("show_graph", self.default_config["show_graph"])
    
    def apply_default_config(self):
        """Applique la configuration par défaut"""
        self.apply_config(self.default_config)
    
    def save_config(self):
        """Sauvegarde la configuration dans le fichier JSON"""
        config = {
            "start_x": self.start_x,
            "start_y": self.start_y,
            "cols": self.cols,
            "rows": self.rows,
            "cell_w": self.cell_w,
            "cell_h": self.cell_h,
            "threshold": self.threshold,
            "color_background": list(self.color_background),
            "color_object": list(self.color_object),
            "color_grid": list(self.color_grid),
            "color_text": list(self.color_text),
            "show_graph": self.show_graph
        }
        
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(config, f, indent=4)
            print(f"\n✅ Configuration sauvegardée dans {CONFIG_FILE}")
        except Exception as e:
            print(f"\n❌ Erreur de sauvegarde: {e}")
    
    # ========================
    # DÉTECTION
    # ========================
    
    def set_reference(self, depth_array):
        """Définit la profondeur de référence (fond)"""
        self.reference_depth = depth_array.copy().astype(np.float32)
        self.reference_set = True
        print("\n✅ Référence de profondeur définie!")
        print("   Tout objet plus proche que le fond sera détecté en rouge")
    
    def detect_objects(self, depth_array):
        """
        Détecte les objets plus proches que la référence
        Retourne un masque binaire (True = objet détecté)
        """
        if not self.reference_set:
            return np.zeros_like(depth_array, dtype=bool)
        
        current = depth_array.astype(np.float32)
        reference = self.reference_depth
        
        valid_current = current > 0
        valid_reference = reference > 0
        closer = current < (reference - self.threshold)
        
        object_mask = valid_current & valid_reference & closer
        
        return object_mask
    
    def calculate_grid_values(self, object_mask):
        """
        Calcule les valeurs binaires de la grille
        1 = objet détecté dans la cellule, 0 = rien
        """
        self.grid_values = np.zeros((self.rows, self.cols), dtype=np.int32)
        
        h, w = object_mask.shape
        
        for row in range(self.rows):
            for col in range(self.cols):
                # Coordonnées de la cellule (adaptées à la résolution sous-échantillonnée)
                x1 = int(self.start_x / self.subsample) + col * int(self.cell_w / self.subsample)
                y1 = int(self.start_y / self.subsample) + row * int(self.cell_h / self.subsample)
                x2 = min(x1 + int(self.cell_w / self.subsample), w)
                y2 = min(y1 + int(self.cell_h / self.subsample), h)
                x1 = max(0, x1)
                y1 = max(0, y1)
                
                if x2 > x1 and y2 > y1:
                    cell_mask = object_mask[y1:y2, x1:x2]
                    
                    if np.any(cell_mask):
                        self.grid_values[row, col] = 1
        
        # Notifier le delegate
        if self.delegate is not None and np.any(self.grid_values):
            self.delegate.process(self.grid_values)
        
        return self.grid_values
    
    # ========================
    # AFFICHAGE
    # ========================
    
    def create_binary_image(self, depth_array, object_mask):
        """
        Crée une image binaire:
        - Bleu = fond (référence)
        - Rouge = objet détecté
        - Noir = pas de données
        """
        h, w = depth_array.shape
        image = np.zeros((h, w, 3), dtype=np.uint8)
        
        valid_pixels = depth_array > 0
        
        image[valid_pixels] = self.color_background
        image[object_mask] = self.color_object
        
        return image
    
    def draw_grid(self, image):
        """Dessine la grille et les valeurs binaires"""
        scale = self.subsample  # Pour adapter les coordonnées
        
        for row in range(self.rows):
            for col in range(self.cols):
                # Coordonnées de la cellule (échelle réduite)
                x1 = int(self.start_x / scale) + col * int(self.cell_w / scale)
                y1 = int(self.start_y / scale) + row * int(self.cell_h / scale)
                x2 = x1 + int(self.cell_w / scale)
                y2 = y1 + int(self.cell_h / scale)
                
                value = self.grid_values[row, col] if self.grid_values is not None else 0
                
                if value == 1:
                    cell_color = self.color_object
                    thickness = 2
                else:
                    cell_color = self.color_grid
                    thickness = 1
                
                cv2.rectangle(image, (x1, y1), (x2, y2), cell_color, thickness)
                
                # Texte au centre
                text = str(value)
                font = cv2.FONT_HERSHEY_SIMPLEX
                font_scale = 0.4
                text_thickness = 1
                
                (tw, th), _ = cv2.getTextSize(text, font, font_scale, text_thickness)
                
                tx = x1 + (int(self.cell_w / scale) - tw) // 2
                ty = y1 + (int(self.cell_h / scale) + th) // 2
                
                text_color = self.color_object if value == 1 else self.color_text
                cv2.putText(image, text, (tx, ty), font, font_scale, text_color, text_thickness)
        
        return image
    
    def draw_help(self, image):
        """Affiche l'aide et les paramètres"""
        ref_status = "DEFINIE" if self.reference_set else "NON DEFINIE"
        ref_color = (0, 255, 0) if self.reference_set else (0, 0, 255)
        
        active_cells = np.sum(self.grid_values) if self.grid_values is not None else 0
        total_cells = self.rows * self.cols
        
        help_text = [
            "=== DETECTION BINAIRE (Pi) ===",
            f"Reference: {ref_status}",
            f"Seuil: {self.threshold}mm",
            f"",
            f"=== GRILLE ===",
            f"Pos: ({self.start_x}, {self.start_y})",
            f"Taille: {self.cols}x{self.rows}",
            f"Cellule: {self.cell_w}x{self.cell_h}px",
            f"Actives: {active_cells}/{total_cells}",
            f"",
            "=== CONTROLES ===",
            "ENTREE: Definir ref",
            "Fleches: Deplacer",
            "+/-: Colonnes",
            "ESPACE: Sauver",
            "Q: Quitter"
        ]
        
        y = 15
        for text in help_text:
            if "Reference:" in text:
                color = ref_color
            elif "Actives:" in text:
                color = (0, 255, 255)
            else:
                color = (255, 255, 255)
            
            cv2.putText(image, text, (5, y), cv2.FONT_HERSHEY_SIMPLEX,
                       0.3, color, 1)
            y += 12
        
        return image
    
    # ========================
    # CLAVIER
    # ========================
    
    def handle_key(self, key):
        """Gère les entrées clavier"""
        # === DÉPLACEMENT ===
        if key == ord('z') or key == ord('Z') or key == 82:  # Haut
            self.start_y = max(0, self.start_y - 10)
        elif key == ord('s') or key == ord('S') or key == 84:  # Bas
            self.start_y = min(424 - self.cell_h, self.start_y + 10)
        elif key == ord('q') or key == 81:  # Gauche (attention conflit avec Quit)
            self.start_x = max(0, self.start_x - 10)
        elif key == ord('d') or key == ord('D') or key == 83:  # Droite
            self.start_x = min(512 - self.cell_w, self.start_x + 10)
        
        # === NOMBRE DE CELLULES ===
        elif key == ord('+') or key == ord('='):
            self.cols = min(20, self.cols + 1)
            print(f"Colonnes: {self.cols}")
        elif key == ord('-'):
            self.cols = max(1, self.cols - 1)
            print(f"Colonnes: {self.cols}")
        elif key == ord('*'):
            self.rows = min(15, self.rows + 1)
            print(f"Lignes: {self.rows}")
        elif key == ord('/'):
            self.rows = max(1, self.rows - 1)
            print(f"Lignes: {self.rows}")
        
        # === TAILLE DES CELLULES ===
        elif key == ord('i') or key == ord('I'):
            self.cell_w = min(200, self.cell_w + 5)
            print(f"Largeur cellule: {self.cell_w}")
        elif key == ord('k') or key == ord('K'):
            self.cell_w = max(20, self.cell_w - 5)
            print(f"Largeur cellule: {self.cell_w}")
        elif key == ord('l') or key == ord('L'):
            self.cell_h = min(200, self.cell_h + 5)
            print(f"Hauteur cellule: {self.cell_h}")
        elif key == ord('j') or key == ord('J'):
            self.cell_h = max(20, self.cell_h - 5)
            print(f"Hauteur cellule: {self.cell_h}")
        
        # === SEUIL ===
        elif key == ord('['):
            self.threshold = max(5, self.threshold - 5)
            print(f"Seuil: {self.threshold}mm")
        elif key == ord(']'):
            self.threshold = min(200, self.threshold + 5)
            print(f"Seuil: {self.threshold}mm")
        
        # === RESET ===
        elif key == ord('r') or key == ord('R'):
            self.apply_default_config()
            self.reference_depth = None
            self.reference_set = False
            print("\n🔄 Tout réinitialisé")
    
    # ========================
    # PARSING KINECT
    # ========================
    
    def _parse_frame(self, line):
        """Parse une ligne FRAME: du programme C++"""
        try:
            if not line.startswith("FRAME:"):
                return None
            
            data_str = line[6:]  # Enlever "FRAME:"
            values = [int(v) for v in data_str.split(",") if v]
            
            # Reconstruire l'array (sous-échantillonné)
            expected_w = self.frame_width // self.subsample
            expected_h = self.frame_height // self.subsample
            expected_size = expected_w * expected_h
            
            if len(values) >= expected_size:
                depth_array = np.array(values[:expected_size], dtype=np.float32)
                depth_array = depth_array.reshape((expected_h, expected_w))
                return depth_array
            
            return None
            
        except Exception as e:
            return None
    
    # ========================
    # BOUCLE PRINCIPALE
    # ========================
    
    def run(self):
        """Boucle principale"""
        print("=" * 60)
        print("DÉTECTION BINAIRE D'OBJETS - KINECT V2 (Raspberry Pi)")
        print("=" * 60)
        print("\n📌 INSTRUCTIONS:")
        print("1. Placez la Kinect face à la scène VIDE (fond)")
        print("2. Appuyez sur ENTRÉE pour définir la référence")
        print("3. Les objets plus proches apparaîtront en ROUGE")
        print("=" * 60)
        
        # Vérifier l'exécutable
        if not os.path.exists(self.capture_bin):
            print(f"❌ Exécutable non trouvé: {self.capture_bin}")
            print("Compile-le avec:")
            print(f"  g++ -std=c++11 depth_capture.cpp -o depth_capture \\")
            print(f"      -I/usr/local/include -L/usr/local/lib -lfreenect2 -lpthread")
            return
        
        # Lancer le processus Kinect
        try:
            self.process = subprocess.Popen(
                [self.capture_bin],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
        except Exception as e:
            print(f"❌ Erreur lancement Kinect: {e}")
            return
        
        self.running = True
        capture_count = 0
        
        # Thread pour lire stderr
        def read_stderr():
            for line in self.process.stderr:
                line = line.strip()
                if line == "READY":
                    print("✅ Kinect v2 prête")
                elif line == "NO_DEVICE":
                    print("❌ Aucune Kinect détectée")
                    self.running = False
                elif line.startswith("SERIAL:"):
                    print(f"📷 Kinect: {line[7:]}")
                elif line.startswith("DIMS:"):
                    dims = line[5:].split(",")
                    self.frame_width = int(dims[0])
                    self.frame_height = int(dims[1])
                    print(f"📐 Résolution: {self.frame_width}x{self.frame_height}")
        
        stderr_thread = threading.Thread(target=read_stderr, daemon=True)
        stderr_thread.start()
        
        # Attendre que la Kinect soit prête
        time.sleep(2)
        
        try:
            for line in self.process.stdout:
                if not self.running:
                    break
                
                line = line.strip()
                
                # Parser la frame
                depth_array = self._parse_frame(line)
                
                if depth_array is None:
                    continue
                
                self.current_depth = depth_array
                
                # Détecter les objets
                object_mask = self.detect_objects(depth_array)
                
                # Calculer les valeurs de la grille
                self.calculate_grid_values(object_mask)
                
                # Créer l'image
                if self.show_graph:
                    image = self.create_binary_image(depth_array, object_mask)
                    image = self.draw_grid(image)
                    image = self.draw_help(image)
                    
                    # Agrandir pour meilleure visibilité
                    image = cv2.resize(image, (512, 424), interpolation=cv2.INTER_NEAREST)
                    
                    cv2.imshow('Detection Binaire (Pi)', image)
                
                # Gestion des touches
                key = cv2.waitKey(1) & 0xFF
                
                if key == 255:
                    continue
                
                # === QUITTER ===
                if key == ord('x') or key == ord('X') or key == 27:  # X ou ESC pour quitter
                    break
                
                # === DÉFINIR LA RÉFÉRENCE ===
                elif key == 13 or key == 10:  # ENTRÉE
                    if self.current_depth is not None:
                        self.set_reference(self.current_depth)
                
                # === SAUVEGARDER CONFIG ===
                elif key == 32:  # ESPACE
                    self.save_config()
                
                # === CAPTURE ===
                elif key == ord('c') or key == ord('C'):
                    if self.grid_values is not None and self.show_graph:
                        img_file = f"capture_{capture_count}.png"
                        cv2.imwrite(img_file, image)
                        
                        grid_file = f"grid_{capture_count}.csv"
                        np.savetxt(grid_file, self.grid_values, delimiter=',', fmt='%d')
                        
                        print(f"\n📸 Sauvegardé: {img_file} et {grid_file}")
                        capture_count += 1
                
                # === AUTRES TOUCHES ===
                else:
                    self.handle_key(key)
                    
        except KeyboardInterrupt:
            print("\n⏹️ Arrêt demandé")
        finally:
            self.stop()
            cv2.destroyAllWindows()
            print("\n✅ Terminé!")
    
    def run_headless(self):
        """
        Boucle principale SANS affichage graphique
        Pour utilisation avec server.py
        """
        print("🚀 Démarrage DepthDetector (mode headless)...")
        
        if not os.path.exists(self.capture_bin):
            print(f"❌ Exécutable non trouvé: {self.capture_bin}")
            return
        
        try:
            self.process = subprocess.Popen(
                [self.capture_bin],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
        except Exception as e:
            print(f"❌ Erreur lancement Kinect: {e}")
            return
        
        self.running = True
        
        # Thread pour lire stderr
        def read_stderr():
            for line in self.process.stderr:
                line = line.strip()
                if line == "READY":
                    print("✅ Kinect v2 prête (headless)")
                elif line == "NO_DEVICE":
                    print("❌ Aucune Kinect détectée")
                    self.running = False
        
        stderr_thread = threading.Thread(target=read_stderr, daemon=True)
        stderr_thread.start()
        
        time.sleep(2)
        
        try:
            for line in self.process.stdout:
                if not self.running:
                    break
                
                depth_array = self._parse_frame(line.strip())
                
                if depth_array is None:
                    continue
                
                self.current_depth = depth_array
                
                object_mask = self.detect_objects(depth_array)
                self.calculate_grid_values(object_mask)
                
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()
    
    def stop(self):
        """Arrête proprement"""
        self.running = False
        
        if self.process is not None:
            print("🛑 Arrêt du processus Kinect...")
            self.process.terminate()
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.process.kill()
            self.process = None
            print("✅ Processus arrêté")


# ========================
# TEST
# ========================

if __name__ == "__main__":
    detector = DepthDetector()
    detector.run()  # Avec affichage graphique