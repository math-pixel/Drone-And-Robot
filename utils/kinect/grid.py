from pykinect2 import PyKinectV2
from pykinect2 import PyKinectRuntime
import numpy as np
import cv2
import json
import os

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
            "bg_color": [0, 0, 0]
        }
        
        # Charger la configuration
        self.load_config()
        
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
            "bg_color": list(self.bg_color)
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
    
    def draw(self, image, averages):
        """Dessine la grille sur l'image"""
        for row in range(self.rows):
            for col in range(self.cols):
                x1 = self.start_x + col * self.cell_w
                y1 = self.start_y + row * self.cell_h
                x2 = x1 + self.cell_w
                y2 = y1 + self.cell_h
                
                # Rectangle
                cv2.rectangle(image, (x1, y1), (x2, y2), self.grid_color, 2)
                
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
                cv2.rectangle(image, (tx-2, ty-th-2), (tx+tw+2, ty+2), self.bg_color, -1)
                # Texte
                cv2.putText(image, text, (tx, ty), font, scale, self.text_color, 1)
        
        return image
    
    def draw_help(self, image):
        """Affiche l'aide et les paramètres actuels"""
        help_text = [
            f"=== PARAMETRES ACTUELS ===",
            f"Position: ({self.start_x}, {self.start_y})",
            f"Grille: {self.cols} x {self.rows} cellules",
            f"Taille cellule: {self.cell_w} x {self.cell_h} px",
            f"",
            f"=== CONTROLES ===",
            f"Fleches: Deplacer la grille",
            f"+ / -: Colonnes | * / /: Lignes",
            f"I/K: Largeur cellule | J/L: Hauteur cellule",
            f"",
            f"ESPACE: Sauvegarder config JSON",
            f"C: Sauvegarder capture PNG + CSV",
            f"R: Reset | Q: Quitter"
        ]
        
        y = 20
        for text in help_text:
            cv2.putText(image, text, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 
                       0.35, (255, 255, 255), 1)
            y += 15
        
        return image
    
    def handle_key(self, key):
        """Gère les entrées clavier"""
        moved = False
        
        # === DÉPLACEMENT (Flèches) ===
        # Flèche Haut (code 0)
        if key == 0:
            self.start_y = max(0, self.start_y - 10)
            moved = True
        # Flèche Bas (code 1)
        elif key == 1:
            self.start_y = min(424 - self.cell_h, self.start_y + 10)
            moved = True
        # Flèche Gauche (code 2) 
        elif key == 2:
            self.start_x = max(0, self.start_x - 10)
            moved = True
        # Flèche Droite (code 3)
        elif key == 3:
            self.start_x = min(512 - self.cell_w, self.start_x + 10)
            moved = True
        
        # === NOMBRE DE CELLULES ===
        elif key == ord('+') or key == ord('='):
            self.cols = min(20, self.cols + 1)
            moved = True
        elif key == ord('-'):
            self.cols = max(1, self.cols - 1)
            moved = True
        elif key == ord('*'):
            self.rows = min(15, self.rows + 1)
            moved = True
        elif key == ord('/'):
            self.rows = max(1, self.rows - 1)
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
        
        # === RESET ===
        elif key == ord('r') or key == ord('R'):
            self.apply_default_config()
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
        print("GRILLE DE PROFONDEUR KINECT V2")
        print("=" * 60)
        print(f"\nConfiguration actuelle:")
        print(f"  Position: ({self.start_x}, {self.start_y})")
        print(f"  Grille: {self.cols} x {self.rows}")
        print(f"  Cellule: {self.cell_w} x {self.cell_h}")
        print("\nAppuyez sur une touche pour voir les contrôles")
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
            
            # Attendre une touche avec waitKeyEx pour les flèches
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
            if key == ord('q') or key == ord('Q') or key == 27:  # Q ou Echap
                break
            
            # === SAUVEGARDER CONFIG JSON ===
            elif key == 32:  # ESPACE
                self.save_config()
            
            # === SAUVEGARDER CAPTURE ===
            elif key == ord('c') or key == ord('C'):
                if last_image is not None and last_averages is not None:
                    # Sauvegarder l'image
                    img_file = f"capture_{capture_count}.png"
                    cv2.imwrite(img_file, last_image)
                    
                    # Sauvegarder les données CSV
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