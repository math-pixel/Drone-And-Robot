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
            # Les 4 coins de la grille (Haut-Gauche, Haut-Droite, Bas-Droite, Bas-Gauche)
            "corners": [
                [100, 100],  # TL
                [400, 100],  # TR
                [450, 350],  # BR
                [50, 350]    # BL
            ],
            
            # Dimensions de la grille
            "cols": 5,
            "rows": 5,
            
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
        
        # === ÉTAT ===
        self.grid_values = None
        self.delegate = delegate
        
        # === SOURIS ===
        self.selected_corner_index = -1  # Aucun coin sélectionné
        self.mouse_pos = (0, 0)

        # Kinect
        self.kinect = PyKinectRuntime.PyKinectRuntime(PyKinectV2.FrameSourceTypes_Depth)
        print("✅ Kinect connectée!")
        
        # Initialiser fenêtre pour la souris
        cv2.namedWindow('Detection Binaire')
        cv2.setMouseCallback('Detection Binaire', self.mouse_callback)
    
    def load_config(self):
        """Charge la configuration"""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                self.apply_config(config)
                print(f"✅ Config chargée")
            except:
                self.apply_default_config()
        else:
            self.apply_default_config()
    
    def apply_config(self, config):
        self.corners = config.get("corners", self.default_config["corners"])
        self.cols = config.get("cols", self.default_config["cols"])
        self.rows = config.get("rows", self.default_config["rows"])
        self.threshold = config.get("threshold", self.default_config["threshold"])
        # Conversion couleurs
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
            print(f"✅ Sauvegardé dans {CONFIG_FILE}")
        except Exception as e:
            print(f"❌ Erreur sauvegarde: {e}")

    def mouse_callback(self, event, x, y, flags, param):
        """Gère le clic et le déplacement des coins"""
        self.mouse_pos = (x, y)
        
        # Rayon de détection du clic
        radius = 20
        
        if event == cv2.EVENT_LBUTTONDOWN:
            # Chercher si on a cliqué proche d'un coin
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
                # Mettre à jour la position du coin
                # On clamp pour rester dans l'image
                cx = max(0, min(self.img_w, x))
                cy = max(0, min(self.img_h, y))
                self.corners[self.selected_corner_index] = [cx, cy]
                
        elif event == cv2.EVENT_LBUTTONUP:
            self.selected_corner_index = -1

    def set_reference(self, depth_array):
        self.reference_depth = depth_array.copy().astype(np.float32)
        self.reference_set = True
        print("✅ Référence définie!")

    def detect_objects(self, depth_array):
        if not self.reference_set:
            return np.zeros_like(depth_array, dtype=bool)
        
        current = depth_array.astype(np.float32)
        reference = self.reference_depth
        
        valid_current = current > 0
        valid_reference = reference > 0
        closer = current < (reference - self.threshold)
        
        return valid_current & valid_reference & closer

    def get_interpolated_point(self, r, c):
        """
        Calcule la position (x,y) d'un point de la grille (row, col)
        en utilisant l'interpolation bilinéaire dans le quadrangle.
        r et c sont des floats entre 0.0 et 1.0
        """
        tl, tr, br, bl = [np.array(p) for p in self.corners]
        
        # Interpolation sur l'axe horizontal (haut et bas)
        top_pt = tl + (tr - tl) * c
        bot_pt = bl + (br - bl) * c
        
        # Interpolation sur l'axe vertical entre les points trouvés
        final_pt = top_pt + (bot_pt - top_pt) * r
        
        return final_pt.astype(int)

    def get_cell_polygon(self, row, col):
        """Retourne les 4 coordonnées d'une cellule spécifique"""
        # Ratios (0.0 à 1.0)
        r0 = row / self.rows
        r1 = (row + 1) / self.rows
        c0 = col / self.cols
        c1 = (col + 1) / self.cols
        
        p1 = self.get_interpolated_point(r0, c0) # TL
        p2 = self.get_interpolated_point(r0, c1) # TR
        p3 = self.get_interpolated_point(r1, c1) # BR
        p4 = self.get_interpolated_point(r1, c0) # BL
        
        return np.array([p1, p2, p3, p4], dtype=np.int32)

    def calculate_grid_values(self, object_mask):
        """Vérifie chaque cellule trapézoïdale"""
        self.grid_values = np.zeros((self.rows, self.cols), dtype=np.int32)
        
        # Optimisation: ne pas recréer l'image noire à chaque cellule si possible
        # Mais pour la clarté, on fait un masque par cellule
        for row in range(self.rows):
            for col in range(self.cols):
                # Obtenir le polygone de la cellule
                pts = self.get_cell_polygon(row, col)
                
                # Créer un masque pour cette cellule unique
                mask = np.zeros((self.img_h, self.img_w), dtype=np.uint8)
                cv2.fillConvexPoly(mask, pts, 255)
                
                # Vérifier intersection avec objets détectés
                # mask > 0 est la zone de la cellule
                # object_mask est True là où il y a un objet
                cell_hits = np.logical_and(mask > 0, object_mask)
                
                if np.count_nonzero(cell_hits) > 5: # Seuil de bruit (pixels min)
                    self.grid_values[row, col] = 1
        
        if self.delegate and self.grid_values is not None:
             self.delegate.process(self.grid_values)
        
        return self.grid_values

    def create_visualization(self, depth_array, object_mask):
        """Crée l'image finale"""
        image = np.zeros((self.img_h, self.img_w, 3), dtype=np.uint8)
        
        # Fond
        image[depth_array > 0] = self.color_background
        image[object_mask] = self.color_object
        
        # Dessiner la grille
        for row in range(self.rows):
            for col in range(self.cols):
                pts = self.get_cell_polygon(row, col)
                val = self.grid_values[row, col] if self.grid_values is not None else 0
                
                color = self.color_object if val == 1 else self.color_grid
                thickness = 2 if val == 1 else 1
                
                # Dessiner le contour de la cellule
                cv2.polylines(image, [pts], True, color, thickness)
                
                # Texte au centre (Moyenne des 4 points)
                center = np.mean(pts, axis=0).astype(int)
                
                # Si activé, on remplit un peu pour voir mieux
                if val == 1:
                    overlay = image.copy()
                    cv2.fillConvexPoly(overlay, pts, self.color_object)
                    cv2.addWeighted(overlay, 0.3, image, 0.7, 0, image)
                
                # Afficher 1 ou 0
                label = str(val)
                cv2.putText(image, label, tuple(center), cv2.FONT_HERSHEY_SIMPLEX, 0.5, self.color_text, 1)

        # Dessiner les coins (poignées) pour l'édition
        for i, corner in enumerate(self.corners):
            c = tuple(corner)
            color = (0, 255, 255) if i == self.selected_corner_index else (255, 255, 0)
            cv2.circle(image, c, 8, color, -1)
            cv2.putText(image, str(i+1), (c[0]-5, c[1]+5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0,0,0), 1)

        return image

    def draw_help(self, image):
        # Affiche infos rapides
        cv2.putText(image, f"Grille: {self.cols}x{self.rows}", (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255), 1)
        cv2.putText(image, "SOURIS: Glisser les coins jaunes", (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,255), 1)
        cv2.putText(image, "ESPACE: Sauvegarder | Q: Quitter", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255), 1)
        return image

    def run(self):
        print("DÉMARRAGE - KINECT GRID POLYGON")
        print("Utilisez la SOURIS pour déplacer les 4 coins.")
        
        while True:
            if self.kinect.has_new_depth_frame():
                frame = self.kinect.get_last_depth_frame()
                depth = frame.reshape((self.img_h, self.img_w)).astype(np.uint16)
                
                # 1. Détection
                mask = self.detect_objects(depth)
                
                # 2. Calcul grille (Polygonale)
                self.calculate_grid_values(mask)
                
                # 3. Visu
                img = self.create_visualization(depth, mask)
                img = self.draw_help(img)
                
                cv2.imshow('Detection Binaire', img)
            
            key = cv2.waitKey(1) & 0xFF
            
            if key == ord('q') or key == 27:
                break
            elif key == 13: # ENTER
                if 'depth' in locals(): self.set_reference(depth)
            elif key == 32: # SPACE
                self.save_config()
            elif key == ord('+'):
                self.cols = min(10, self.cols + 1)
            elif key == ord('-'):
                self.cols = max(1, self.cols - 1)
            elif key == ord('*'):
                self.rows = min(10, self.rows + 1)
            elif key == ord('/'):
                self.rows = max(1, self.rows - 1)
            elif key == ord('r'):
                self.apply_default_config()

        cv2.destroyAllWindows()
        self.kinect.close()

if __name__ == "__main__":
    detector = DepthDetector()
    detector.run()