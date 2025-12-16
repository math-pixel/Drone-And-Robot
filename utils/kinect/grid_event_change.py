from pykinect2 import PyKinectV2
from pykinect2 import PyKinectRuntime
import numpy as np
import cv2
import json
import os
import time

# Fichier de configuration
CONFIG_FILE = "grid_config.json"

class DepthGrid:
    def __init__(self):
        # Valeurs par défaut
        self.default_config = {
            "start_x": 50,
            "start_y": 50,
            "cols": 5,
            "rows": 4,
            "cell_w": 80,
            "cell_h": 70,
            "grid_color": [0, 255, 0],
            "text_color": [255, 255, 255],
            "bg_color": [0, 0, 0],
            "detection_enabled": True,
            "detection_threshold": 50,  # Seuil en mm (5cm = 50mm)
            "alert_duration": 1.0       # Durée de l'alerte en secondes
        }
        
        # Charger la configuration
        self.load_config()
        
        # === DÉTECTION DE CHANGEMENT ===
        self.previous_averages = None
        self.alert_matrix = None          # Matrice des temps d'alerte par cellule
        self.alert_color = (0, 0, 255)    # Rouge pour l'alerte
        
        # Kinect
        self.kinect = PyKinectRuntime.PyKinectRuntime(
            PyKinectV2.FrameSourceTypes_Depth
        )
        
        print("✅ Kinect connectée!")
    
    def load_config(self):
        """Charge la configuration depuis le fichier JSON"""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                print(f"✅ Configuration chargée depuis {CONFIG_FILE}")
                
                # Appliquer les valeurs
                self.start_x = config.get("start_x", self.default_config["start_x"])
                self.start_y = config.get("start_y", self.default_config["start_y"])
                self.cols = config.get("cols", self.default_config["cols"])
                self.rows = config.get("rows", self.default_config["rows"])
                self.cell_w = config.get("cell_w", self.default_config["cell_w"])
                self.cell_h = config.get("cell_h", self.default_config["cell_h"])
                self.grid_color = tuple(config.get("grid_color", self.default_config["grid_color"]))
                self.text_color = tuple(config.get("text_color", self.default_config["text_color"]))
                self.bg_color = tuple(config.get("bg_color", self.default_config["bg_color"]))
                self.detection_enabled = config.get("detection_enabled", self.default_config["detection_enabled"])
                self.detection_threshold = config.get("detection_threshold", self.default_config["detection_threshold"])
                self.alert_duration = config.get("alert_duration", self.default_config["alert_duration"])
                
            except Exception as e:
                print(f"⚠️ Erreur de lecture du JSON: {e}")
                self.apply_default_config()
        else:
            print(f"ℹ️ Pas de fichier {CONFIG_FILE}, utilisation des valeurs par défaut")
            self.apply_default_config()
    
    def apply_default_config(self):
        """Applique la configuration par défaut"""
        self.start_x = self.default_config["start_x"]
        self.start_y = self.default_config["start_y"]
        self.cols = self.default_config["cols"]
        self.rows = self.default_config["rows"]
        self.cell_w = self.default_config["cell_w"]
        self.cell_h = self.default_config["cell_h"]
        self.grid_color = tuple(self.default_config["grid_color"])
        self.text_color = tuple(self.default_config["text_color"])
        self.bg_color = tuple(self.default_config["bg_color"])
        self.detection_enabled = self.default_config["detection_enabled"]
        self.detection_threshold = self.default_config["detection_threshold"]
        self.alert_duration = self.default_config["alert_duration"]
    
    def save_config(self):
        """Sauvegarde la configuration dans le fichier JSON"""
        config = {
            "start_x": self.start_x,
            "start_y": self.start_y,
            "cols": self.cols,
            "rows": self.rows,
            "cell_w": self.cell_w,
            "cell_h": self.cell_h,
            "grid_color": list(self.grid_color),
            "text_color": list(self.text_color),
            "bg_color": list(self.bg_color),
            "detection_enabled": self.detection_enabled,
            "detection_threshold": self.detection_threshold,
            "alert_duration": self.alert_duration
        }
        
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(config, f, indent=4)
            print(f"\n✅ Configuration sauvegardée dans {CONFIG_FILE}")
        except Exception as e:
            print(f"\n❌ Erreur de sauvegarde: {e}")
    
    def calculate_averages(self, depth_array):
        """Calcule les moyennes pour chaque cellule"""
        averages = np.zeros((self.rows, self.cols), dtype=np.float32)
        
        for row in range(self.rows):
            for col in range(self.cols):
                x1 = self.start_x + col * self.cell_w
                y1 = self.start_y + row * self.cell_h
                x2 = min(x1 + self.cell_w, 512)
                y2 = min(y1 + self.cell_h, 424)
                x1 = max(0, x1)
                y1 = max(0, y1)
                
                if x2 > x1 and y2 > y1:
                    cell = depth_array[y1:y2, x1:x2]
                    valid = cell[(cell > 0) & (cell < 8000)]
                    
                    if len(valid) > 0:
                        averages[row, col] = np.mean(valid)
        
        return averages
    
    def detect_changes(self, current_averages):
        """
        Détecte les changements de profondeur supérieurs au seuil
        Met à jour la matrice d'alertes
        """
        current_time = time.time()
        
        # Initialiser la matrice d'alertes si nécessaire
        if self.alert_matrix is None or self.alert_matrix.shape != (self.rows, self.cols):
            self.alert_matrix = np.zeros((self.rows, self.cols), dtype=np.float64)
        
        # Si pas de mesure précédente, initialiser
        if self.previous_averages is None or self.previous_averages.shape != current_averages.shape:
            self.previous_averages = current_averages.copy()
            return
        
        # Comparer avec les valeurs précédentes
        for row in range(self.rows):
            for col in range(self.cols):
                current_val = current_averages[row, col]
                previous_val = self.previous_averages[row, col]
                
                # Ignorer si une des valeurs est invalide
                if current_val == 0 or previous_val == 0:
                    continue
                
                # Calculer la différence
                diff = abs(current_val - previous_val)
                
                # Si le changement dépasse le seuil
                if diff > self.detection_threshold:
                    self.alert_matrix[row, col] = current_time
                    print(f"\n🚨 ALERTE [{row},{col}]: Changement de {diff:.0f}mm détecté!")
        
        # Mettre à jour les valeurs précédentes
        self.previous_averages = current_averages.copy()
    
    def is_cell_alerting(self, row, col):
        """Vérifie si une cellule est en état d'alerte"""
        if self.alert_matrix is None:
            return False
        
        if row >= self.alert_matrix.shape[0] or col >= self.alert_matrix.shape[1]:
            return False
        
        alert_time = self.alert_matrix[row, col]
        if alert_time == 0:
            return False
        
        # Vérifier si l'alerte est encore active
        elapsed = time.time() - alert_time
        return elapsed < self.alert_duration
    
    def get_cell_color(self, row, col):
        """Retourne la couleur de la cellule (rouge si alerte, sinon normale)"""
        if self.detection_enabled and self.is_cell_alerting(row, col):
            return self.alert_color
        return self.grid_color
    
    def draw(self, image, averages):
        """Dessine la grille sur l'image"""
        for row in range(self.rows):
            for col in range(self.cols):
                x1 = self.start_x + col * self.cell_w
                y1 = self.start_y + row * self.cell_h
                x2 = x1 + self.cell_w
                y2 = y1 + self.cell_h
                
                # Couleur de la cellule (rouge si alerte)
                cell_color = self.get_cell_color(row, col)
                
                # Si en alerte, remplir le fond en rouge semi-transparent
                if self.detection_enabled and self.is_cell_alerting(row, col):
                    overlay = image.copy()
                    cv2.rectangle(overlay, (x1, y1), (x2, y2), self.alert_color, -1)
                    cv2.addWeighted(overlay, 0.3, image, 0.7, 0, image)
                
                # Rectangle de contour
                thickness = 3 if self.is_cell_alerting(row, col) else 2
                cv2.rectangle(image, (x1, y1), (x2, y2), cell_color, thickness)
                
                # Texte au centre
                avg = averages[row, col]
                if avg >= 1000:
                    text = f"{avg/1000:.2f}m"
                elif avg > 0:
                    text = f"{int(avg)}"
                else:
                    text = "---"
                
                font = cv2.FONT_HERSHEY_SIMPLEX
                scale = 0.4
                (tw, th), _ = cv2.getTextSize(text, font, scale, 1)
                
                tx = x1 + (self.cell_w - tw) // 2
                ty = y1 + (self.cell_h + th) // 2
                
                # Fond
                bg = self.alert_color if self.is_cell_alerting(row, col) else self.bg_color
                cv2.rectangle(image, (tx-2, ty-th-2), (tx+tw+2, ty+2), bg, -1)
                
                # Texte
                cv2.putText(image, text, (tx, ty), font, scale, self.text_color, 1)
        
        return image
    
    def draw_help(self, image):
        """Affiche l'aide et les paramètres actuels"""
        # État de la détection
        detection_status = "ON ✓" if self.detection_enabled else "OFF ✗"
        detection_color = (0, 255, 0) if self.detection_enabled else (0, 0, 255)
        
        help_text = [
            f"=== PARAMETRES ===",
            f"Position: ({self.start_x}, {self.start_y})",
            f"Grille: {self.cols} x {self.rows} cellules",
            f"Taille cellule: {self.cell_w} x {self.cell_h} px",
            f"",
            f"=== DETECTION ===",
            f"Detection: {detection_status}",
            f"Seuil: {self.detection_threshold} mm ({self.detection_threshold/10:.1f} cm)",
            f"Duree alerte: {self.alert_duration} sec",
            f"",
            f"=== CONTROLES ===",
            f"Fleches/ZQSD: Deplacer",
            f"+/-: Colonnes | *//: Lignes",
            f"I/K: Largeur | L/J: Hauteur",
            f"",
            f"T: Toggle detection ON/OFF",
            f"[/]: Seuil -/+ 10mm",
            f"ESPACE: Sauver JSON | C: Capture",
            f"R: Reset | Q: Quitter"
        ]
        
        y = 20
        for i, text in enumerate(help_text):
            # Colorer la ligne de détection
            if "Detection:" in text:
                cv2.putText(image, text, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 
                           0.35, detection_color, 1)
            else:
                cv2.putText(image, text, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 
                           0.35, (255, 255, 255), 1)
            y += 15
        
        return image
    
    def reset_detection(self):
        """Réinitialise la détection (efface l'historique)"""
        self.previous_averages = None
        self.alert_matrix = None
        print("\n🔄 Détection réinitialisée")
    
    def handle_key(self, key):
        """Gère les entrées clavier"""
        moved = False
        
        # === DÉPLACEMENT (ZQSD + Flèches) ===
        if key == 0 or key == ord('z') or key == ord('Z'):
            self.start_y = max(0, self.start_y - 10)
            moved = True
        elif key == 1:
            self.start_y = min(424 - self.cell_h, self.start_y + 10)
            moved = True
        elif key == 2 or key == ord('a') or key == ord('A'):
            self.start_x = max(0, self.start_x - 10)
            moved = True
        elif key == 3 or key == ord('d') or key == ord('D'):
            self.start_x = min(512 - self.cell_w, self.start_x + 10)
            moved = True
        
        # === NOMBRE DE CELLULES ===
        elif key == ord('+') or key == ord('='):
            self.cols = min(20, self.cols + 1)
            self.reset_detection()
            moved = True
        elif key == ord('-'):
            self.cols = max(1, self.cols - 1)
            self.reset_detection()
            moved = True
        elif key == ord('*'):
            self.rows = min(15, self.rows + 1)
            self.reset_detection()
            moved = True
        elif key == ord('/'):
            self.rows = max(1, self.rows - 1)
            self.reset_detection()
            moved = True
        
        # === TAILLE DES CELLULES ===
        elif key == ord('i') or key == ord('I'):
            self.cell_w = min(200, self.cell_w + 5)
            moved = True
        elif key == ord('k') or key == ord('K'):
            self.cell_w = max(20, self.cell_w - 5)
            moved = True
        elif key == ord('l') or key == ord('L'):
            self.cell_h = min(200, self.cell_h + 5)
            moved = True
        elif key == ord('j') or key == ord('J'):
            self.cell_h = max(20, self.cell_h - 5)
            moved = True
        
        # === TOGGLE DÉTECTION ===
        elif key == ord('t') or key == ord('T'):
            self.detection_enabled = not self.detection_enabled
            status = "ACTIVÉE" if self.detection_enabled else "DÉSACTIVÉE"
            print(f"\n🔔 Détection {status}")
            self.reset_detection()
        
        # === MODIFIER LE SEUIL ===
        elif key == ord('['):
            self.detection_threshold = max(5, self.detection_threshold - 5)
            print(f"\n📏 Seuil: {self.detection_threshold}mm ({self.detection_threshold/10:.1f}cm)")
        elif key == ord(']'):
            self.detection_threshold = min(500, self.detection_threshold + 5)
            print(f"\n📏 Seuil: {self.detection_threshold}mm ({self.detection_threshold/10:.1f}cm)")
        
        # === MODIFIER LA DURÉE D'ALERTE ===
        elif key == ord('{'):
            self.alert_duration = max(0.1, self.alert_duration - 0.1)
            print(f"\n⏱️ Durée alerte: {self.alert_duration:.1f}s")
        elif key == ord('}'):
            self.alert_duration = min(5.0, self.alert_duration + 0.1)
            print(f"\n⏱️ Durée alerte: {self.alert_duration:.1f}s")
        
        # === RESET ===
        elif key == ord('r') or key == ord('R'):
            self.apply_default_config()
            self.reset_detection()
            print("\n🔄 Configuration réinitialisée")
            moved = True
        
        if moved:
            print(f"Position: ({self.start_x}, {self.start_y}) | "
                  f"Grille: {self.cols}x{self.rows} | "
                  f"Cellule: {self.cell_w}x{self.cell_h}", end='\r')
        
        return moved
    
    def run(self):
        """Boucle principale"""
        print("=" * 60)
        print("GRILLE DE PROFONDEUR KINECT V2 - AVEC DÉTECTION")
        print("=" * 60)
        print(f"\nConfiguration actuelle:")
        print(f"  Position: ({self.start_x}, {self.start_y})")
        print(f"  Grille: {self.cols} x {self.rows}")
        print(f"  Cellule: {self.cell_w} x {self.cell_h}")
        print(f"  Détection: {'ON' if self.detection_enabled else 'OFF'}")
        print(f"  Seuil: {self.detection_threshold}mm ({self.detection_threshold/10:.1f}cm)")
        print(f"  Durée alerte: {self.alert_duration}s")
        print("\nAppuyez sur T pour activer/désactiver la détection")
        print("=" * 60)
        
        capture_count = 0
        last_image = None
        last_averages = None
        
        while True:
            if self.kinect.has_new_depth_frame():
                # Profondeur
                depth = self.kinect.get_last_depth_frame()
                depth = depth.reshape((424, 512)).astype(np.uint16)
                
                # Moyennes
                averages = self.calculate_averages(depth)
                last_averages = averages
                
                # Détection de changement
                if self.detection_enabled:
                    self.detect_changes(averages)
                
                # Image
                img = np.clip(depth, 500, 4500)
                img = ((img - 500) / 4000 * 255).astype(np.uint8)
                img = cv2.applyColorMap(img, cv2.COLORMAP_JET)
                img[depth == 0] = [0, 0, 0]
                
                # Dessiner
                img = self.draw(img, averages)
                img = self.draw_help(img)
                
                last_image = img.copy()
                
                cv2.imshow('Grille de Profondeur', img)
            
            # Attendre une touche
            key = cv2.waitKeyEx(1)
            
            if key == -1:
                continue
            
            # Convertir les codes des flèches
            if key == 2490368:    # Flèche Haut
                key = 0
            elif key == 2621440:  # Flèche Bas
                key = 1
            elif key == 2424832:  # Flèche Gauche
                key = 2
            elif key == 2555904:  # Flèche Droite
                key = 3
            
            # === QUITTER ===
            if key == ord('q') or key == ord('Q') or key == 27:
                break
            
            # === SAUVEGARDER CONFIG JSON ===
            elif key == 32:  # ESPACE
                self.save_config()
            
            # === SAUVEGARDER CAPTURE ===
            elif key == ord('c') or key == ord('C'):
                if last_image is not None and last_averages is not None:
                    img_file = f"capture_{capture_count}.png"
                    cv2.imwrite(img_file, last_image)
                    
                    csv_file = f"grid_data_{capture_count}.csv"
                    np.savetxt(csv_file, last_averages, delimiter=',', fmt='%.1f')
                    
                    print(f"\n📸 Sauvegardé: {img_file} et {csv_file}")
                    capture_count += 1
            
            # === AUTRES TOUCHES ===
            else:
                self.handle_key(key)
        
        cv2.destroyAllWindows()
        print("\n✅ Terminé!")


if __name__ == "__main__":
    grid = DepthGrid()
    grid.run()