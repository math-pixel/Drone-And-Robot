from pykinect2 import PyKinectV2
from pykinect2 import PyKinectRuntime
import numpy as np
import cv2
import json
import os
import time

# Fichier de configuration
CONFIG_FILE = "grid_poly_config.json"

class DepthDetector:
    def __init__(self, delegate=None):
        # Dimensions image Kinect V2
        self.img_w = 512
        self.img_h = 424
        
        # Valeurs par défaut
        self.default_config = {
            # Les 4 coins (Haut-Gauche, Haut-Droite, Bas-Droite, Bas-Gauche)
            "corners": [
                [100, 100],  # TL (Top-Left)
                [400, 100],  # TR (Top-Right)
                [400, 350],  # BR (Bottom-Right)
                [100, 350]   # BL (Bottom-Left)
            ],
            
            # Dimensions de la grille
            "cols": 5,
            "rows": 4,
            
            # Détection
            "threshold": 10,          # Seuil en mm
            "threshold_max": 500,
            "threshold_min": 5,
            
            # Couleurs (BGR)
            "color_background": [255, 100, 0],
            "color_object": [0, 0, 255],
            "color_grid": [0, 255, 0],
            "color_text": [255, 255, 255]
        }
        
        # Charger la configuration
        self.load_config()
        
        # === RÉFÉRENCE DE PROFONDEUR ===
        self.reference_depth = None
        self.reference_set = False
        self.current_depth = None
        
        # === ÉTAT ===
        self.grid_values = None
        self.delegate = delegate
        
        # === SOURIS ===
        self.selected_corner_index = -1
        self.mouse_pos = (0, 0)

        # Kinect
        self.kinect = PyKinectRuntime.PyKinectRuntime(PyKinectV2.FrameSourceTypes_Depth)
        print("✅ Kinect connectée!")
        
        # Initialiser fenêtre pour la souris
        cv2.namedWindow('Detection Binaire')
        cv2.setMouseCallback('Detection Binaire', self.mouse_callback)
    
    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                self.apply_config(config)
                print(f"✅ Configuration chargée")
            except Exception as e:
                print(f"⚠️ Erreur JSON: {e}")
                self.apply_default_config()
        else:
            self.apply_default_config()
    
    def apply_config(self, config):
        self.corners = config.get("corners", self.default_config["corners"])
        self.cols = config.get("cols", self.default_config["cols"])
        self.rows = config.get("rows", self.default_config["rows"])
        self.threshold = config.get("threshold", self.default_config["threshold"])
        self.color_background = tuple(config.get("color_background", self.default_config["color_background"]))
        self.color_object = tuple(config.get("color_object", self.default_config["color_object"]))
        self.color_grid = tuple(config.get("color_grid", self.default_config["color_grid"]))
        self.color_text = tuple(config.get("color_text", self.default_config["color_text"]))
    
    def apply_default_config(self):
        self.apply_config(self.default_config)
    
    def save_config(self):
        config = {
            "corners": self.corners,
            "cols": self.cols,
            "rows": self.rows,
            "threshold": self.threshold,
            "color_background": list(self.color_background),
            "color_object": list(self.color_object),
            "color_grid": list(self.color_grid),
            "color_text": list(self.color_text),
        }
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(config, f, indent=4)
            print(f"\n✅ Sauvegardé dans {CONFIG_FILE}")
        except Exception as e:
            print(f"\n❌ Erreur sauvegarde: {e}")

    # === GESTION SOURIS ===
    def mouse_callback(self, event, x, y, flags, param):
        self.mouse_pos = (x, y)
        radius = 20
        
        if event == cv2.EVENT_LBUTTONDOWN:
            best_dist = float('inf')
            best_idx = -1
            for i, corner in enumerate(self.corners):
                dist = np.sqrt((corner[0]-x)**2 + (corner[1]-y)**2)
                if dist < radius and dist < best_dist:
                    best_dist = dist
                    best_idx = i
            if best_idx != -1:
                self.selected_corner_index = best_idx
                
        elif event == cv2.EVENT_MOUSEMOVE:
            if self.selected_corner_index != -1:
                cx = max(0, min(self.img_w, x))
                cy = max(0, min(self.img_h, y))
                self.corners[self.selected_corner_index] = [cx, cy]
                
        elif event == cv2.EVENT_LBUTTONUP:
            self.selected_corner_index = -1

    # === MATHÉMATIQUES GRILLE ===
    def get_interpolated_point(self, r, c):
        """Interpolation bilinéaire pour trouver un point dans le trapèze"""
        tl, tr, br, bl = [np.array(p) for p in self.corners]
        top_pt = tl + (tr - tl) * c
        bot_pt = bl + (br - bl) * c
        final_pt = top_pt + (bot_pt - top_pt) * r
        return final_pt.astype(int)

    def get_cell_polygon(self, row, col):
        """Retourne les 4 coordonnées d'une cellule"""
        r0, r1 = row / self.rows, (row + 1) / self.rows
        c0, c1 = col / self.cols, (col + 1) / self.cols
        
        return np.array([
            self.get_interpolated_point(r0, c0), # TL
            self.get_interpolated_point(r0, c1), # TR
            self.get_interpolated_point(r1, c1), # BR
            self.get_interpolated_point(r1, c0)  # BL
        ], dtype=np.int32)

    # === LOGIQUE MÉTIER ===
    def set_reference(self, depth_array):
        self.reference_depth = depth_array.copy().astype(np.float32)
        self.reference_set = True
        print("\n✅ Référence de profondeur définie!")

    def detect_objects(self, depth_array):
        if not self.reference_set:
            return np.zeros_like(depth_array, dtype=bool)
        
        current = depth_array.astype(np.float32)
        reference = self.reference_depth
        return (current > 0) & (reference > 0) & (current < (reference - self.threshold))

    def calculate_grid_values(self, object_mask):
        self.grid_values = np.zeros((self.rows, self.cols), dtype=np.int32)
        
        for row in range(self.rows):
            for col in range(self.cols):
                pts = self.get_cell_polygon(row, col)
                
                # Masque local pour la forme de la cellule
                mask = np.zeros((self.img_h, self.img_w), dtype=np.uint8)
                cv2.fillConvexPoly(mask, pts, 255)
                
                # Intersection
                cell_hits = np.logical_and(mask > 0, object_mask)
                
                # Seuil de pixels pour éviter le bruit
                if np.count_nonzero(cell_hits) > 5:
                    self.grid_values[row, col] = 1
                    if self.delegate: self.delegate.process(self.grid_values)
        return self.grid_values

    # === AFFICHAGE ===
    def create_visualization(self, depth_array, object_mask):
        image = np.zeros((self.img_h, self.img_w, 3), dtype=np.uint8)
        
        # Fond et Objets
        image[depth_array > 0] = self.color_background
        image[object_mask] = self.color_object
        
        # Grille
        for row in range(self.rows):
            for col in range(self.cols):
                pts = self.get_cell_polygon(row, col)
                val = self.grid_values[row, col] if self.grid_values is not None else 0
                
                color = self.color_object if val == 1 else self.color_grid
                thickness = 2 if val == 1 else 1
                
                cv2.polylines(image, [pts], True, color, thickness)
                
                # Texte
                center = np.mean(pts, axis=0).astype(int)
                label = str(val)
                text_color = self.color_text if val == 0 else self.color_object
                cv2.putText(image, label, tuple(center), cv2.FONT_HERSHEY_SIMPLEX, 0.6, text_color, 2)

        # Coins (Poignées)
        for i, corner in enumerate(self.corners):
            c = tuple(corner)
            color = (0, 255, 255) if i == self.selected_corner_index else (255, 255, 0)
            cv2.circle(image, c, 6, color, -1)
            
        return image

    def draw_help(self, image):
        ref_status = "OK" if self.reference_set else "NON"
        ref_color = (0, 255, 0) if self.reference_set else (0, 0, 255)
        
        texts = [
            f"REF: {ref_status} | Seuil: {self.threshold}mm",
            f"Grille: {self.cols}x{self.rows}",
            "",
            "[SOURIS]: Deplacer coins",
            "[FLECHES]: Bouger tout",
            "[I/K]: Hauteur | [L/J]: Largeur",
            "[+/-]: Cols | [*//]: Lignes",
            "[ESPACE]: Sauver | [C]: Photo",
            "[ENTREE]: Definir Reference"
        ]
        
        y = 20
        for i, t in enumerate(texts):
            c = ref_color if i == 0 else (255, 255, 255)
            cv2.putText(image, t, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.4, c, 1)
            y += 15
        return image

    # === GESTION CLAVIER ===
    def handle_key(self, key):
        step = 5 # Pas de déplacement en pixels
        
        # --- DEPLACEMENT GLOBAL (FLECHES) ---
        dx, dy = 0, 0
        if key == 0 or key == ord('z'): dy = -step    # Haut
        elif key == 1 or key == ord('s'): dy = step   # Bas
        elif key == 2 or key == ord('q'): dx = -step  # Gauche
        elif key == 3 or key == ord('d'): dx = step   # Droite
        
        if dx != 0 or dy != 0:
            for i in range(4):
                self.corners[i][0] = max(0, min(self.img_w, self.corners[i][0] + dx))
                self.corners[i][1] = max(0, min(self.img_h, self.corners[i][1] + dy))

        # --- REDIMENSIONNEMENT (I/K/L/J) ---
        # I/K : Étire ou contracte verticalement
        elif key == ord('i'): # Plus grand en Y
            self.corners[0][1] -= step; self.corners[1][1] -= step # Haut monte
            self.corners[2][1] += step; self.corners[3][1] += step # Bas descend
        elif key == ord('k'): # Plus petit en Y
            self.corners[0][1] += step; self.corners[1][1] += step
            self.corners[2][1] -= step; self.corners[3][1] -= step
        
        # L/J : Étire ou contracte horizontalement
        elif key == ord('l'): # Plus grand en X
            self.corners[0][0] -= step; self.corners[3][0] -= step # Gauche -> gauche
            self.corners[1][0] += step; self.corners[2][0] += step # Droite -> droite
        elif key == ord('j'): # Plus petit en X
            self.corners[0][0] += step; self.corners[3][0] += step
            self.corners[1][0] -= step; self.corners[2][0] -= step

        # --- NOMBRE DE CELLULES ---
        elif key == ord('+') or key == ord('='): self.cols = min(20, self.cols + 1)
        elif key == ord('-'): self.cols = max(1, self.cols - 1)
        elif key == ord('*'): self.rows = min(15, self.rows + 1)
        elif key == ord('/'): self.rows = max(1, self.rows - 1)
        
        # --- SEUIL ---
        elif key == ord('['): 
            self.threshold = max(5, self.threshold - 5)
            print(f"Seuil: {self.threshold}")
        elif key == ord(']'): 
            self.threshold = min(500, self.threshold + 5)
            print(f"Seuil: {self.threshold}")
            
        # --- RESET ---
        elif key == ord('r'):
            self.apply_default_config()
            self.reference_depth = None
            self.reference_set = False

    def run(self):
        print("="*40)
        print("  GRID DETECTION (4 POINTS / TRAPÈZE)")
        print("="*40)
        
        capture_count = 0
        self.current_depth = None
        
        while True:
            if self.kinect.has_new_depth_frame():
                frame = self.kinect.get_last_depth_frame()
                self.current_depth = frame.reshape((self.img_h, self.img_w)).astype(np.uint16)
                
                # Traitement
                mask = self.detect_objects(self.current_depth)
                self.calculate_grid_values(mask)
                img = self.create_visualization(self.current_depth, mask)
                img = self.draw_help(img)
                
                cv2.imshow('Detection Binaire', img)
            
            # Gestion touches
            key = cv2.waitKeyEx(1)
            if key == -1: continue
            
            # Mapping touches flèches Windows/Linux
            if key == 2490368: key = 0   # Up
            elif key == 2621440: key = 1 # Down
            elif key == 2424832: key = 2 # Left
            elif key == 2555904: key = 3 # Right
            
            if key == 27 or key == ord('Q') or key == ord('q'): # Quitter
                break
            elif key == 13: # Entrée
                if self.current_depth is not None: self.set_reference(self.current_depth)
            elif key == 32: # Espace
                self.save_config()
            elif key == ord('c') or key == ord('C'): # Capture
                cv2.imwrite(f"capture_{capture_count}.png", img)
                np.savetxt(f"grid_{capture_count}.csv", self.grid_values, fmt='%d', delimiter=',')
                print(f"📸 Capture {capture_count} sauvegardée")
                capture_count += 1
            else:
                self.handle_key(key)
        
        cv2.destroyAllWindows()
        self.kinect.close()

if __name__ == "__main__":
    detector = DepthDetector()
    detector.run()