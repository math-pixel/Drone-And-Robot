from pykinect2 import PyKinectV2
from pykinect2 import PyKinectRuntime
import numpy as np
import cv2
import json
import os
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
        }
        
        # Charger la configuration
        self.load_config()
        
        # === RÉFÉRENCE DE PROFONDEUR ===
        self.reference_depth = None       # Profondeur de référence (fond)
        self.reference_set = False        # Flag si référence définie
        
        # === ÉTAT DE LA GRILLE ===
        self.grid_values = None           # Valeurs binaires de la grille (0 ou 1)
        self.delegate = None

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
        }
        
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(config, f, indent=4)
            print(f"\n✅ Configuration sauvegardée dans {CONFIG_FILE}")
        except Exception as e:
            print(f"\n❌ Erreur de sauvegarde: {e}")
    
    def set_reference(self, depth_array):
        """Définit la profondeur de référence (fond)"""
        # Copier la profondeur actuelle comme référence
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
        
        # Convertir en float pour les calculs
        current = depth_array.astype(np.float32)
        reference = self.reference_depth
        
        # Un objet est détecté si:
        # 1. La profondeur actuelle est valide (> 0)
        # 2. La profondeur de référence est valide (> 0)
        # 3. L'objet est plus PROCHE que la référence (profondeur plus petite)
        # 4. La différence dépasse le seuil
        
        valid_current = current > 0
        valid_reference = reference > 0
        closer = current < (reference - self.threshold)
        
        # Masque binaire des objets détectés
        object_mask = valid_current & valid_reference & closer
        
        return object_mask
    
    def calculate_grid_values(self, object_mask):
        """
        Calcule les valeurs binaires de la grille
        1 = objet détecté dans la cellule, 0 = rien
        """
        self.grid_values = np.zeros((self.rows, self.cols), dtype=np.int32)
        
        for row in range(self.rows):
            for col in range(self.cols):
                # Coordonnées de la cellule
                x1 = self.start_x + col * self.cell_w
                y1 = self.start_y + row * self.cell_h
                x2 = min(x1 + self.cell_w, 512)
                y2 = min(y1 + self.cell_h, 424)
                x1 = max(0, x1)
                y1 = max(0, y1)
                
                if x2 > x1 and y2 > y1:
                    # Extraire la région du masque
                    cell_mask = object_mask[y1:y2, x1:x2]
                    
                    # Si au moins un pixel est détecté → valeur = 1
                    if np.any(cell_mask):
                        self.grid_values[row, col] = 1
                        self.delegate and self.delegate.process(self.grid_values)
        
        return self.grid_values
    
    def create_binary_image(self, depth_array, object_mask):
        """
        Crée une image binaire:
        - Bleu = fond (référence)
        - Rouge = objet détecté
        - Noir = pas de données
        """
        # Créer une image de la taille de la profondeur
        image = np.zeros((424, 512, 3), dtype=np.uint8)
        
        # Pixels valides (profondeur > 0)
        valid_pixels = depth_array > 0
        
        # Colorier le fond en bleu
        image[valid_pixels] = self.color_background
        
        # Colorier les objets détectés en rouge
        image[object_mask] = self.color_object
        
        return image
    
    def draw_grid(self, image):
        """Dessine la grille et les valeurs binaires"""
        for row in range(self.rows):
            for col in range(self.cols):
                # Coordonnées de la cellule
                x1 = self.start_x + col * self.cell_w
                y1 = self.start_y + row * self.cell_h
                x2 = x1 + self.cell_w
                y2 = y1 + self.cell_h
                
                # Valeur de la cellule
                value = self.grid_values[row, col] if self.grid_values is not None else 0
                
                # Couleur du contour selon la valeur
                if value == 1:
                    cell_color = self.color_object  # Rouge si objet
                    thickness = 3
                else:
                    cell_color = self.color_grid    # Vert sinon
                    thickness = 2
                
                # Dessiner le rectangle
                cv2.rectangle(image, (x1, y1), (x2, y2), cell_color, thickness)
                
                # Texte au centre (0 ou 1)
                text = str(value)
                font = cv2.FONT_HERSHEY_SIMPLEX
                scale = 0.8
                text_thickness = 2
                
                (tw, th), _ = cv2.getTextSize(text, font, scale, text_thickness)
                
                tx = x1 + (self.cell_w - tw) // 2
                ty = y1 + (self.cell_h + th) // 2
                
                # Fond pour le texte
                padding = 5
                cv2.rectangle(image, 
                             (tx - padding, ty - th - padding),
                             (tx + tw + padding, ty + padding),
                             (0, 0, 0), -1)
                
                # Couleur du texte selon la valeur
                text_color = self.color_object if value == 1 else self.color_text
                cv2.putText(image, text, (tx, ty), font, scale, text_color, text_thickness)
        
        return image
    
    def draw_help(self, image):
        """Affiche l'aide et les paramètres"""
        # État de la référence
        ref_status = "DEFINIE ✓" if self.reference_set else "NON DEFINIE ✗"
        ref_color = (0, 255, 0) if self.reference_set else (0, 0, 255)
        
        # Compter les cellules actives
        active_cells = np.sum(self.grid_values) if self.grid_values is not None else 0
        total_cells = self.rows * self.cols
        
        help_text = [
            "=== DETECTION BINAIRE ===",
            f"Reference: {ref_status}",
            f"Seuil: {self.threshold}mm ({self.threshold/10:.1f}cm)",
            f"",
            f"=== GRILLE ===",
            f"Position: ({self.start_x}, {self.start_y})",
            f"Taille: {self.cols}x{self.rows} cellules",
            f"Cellule: {self.cell_w}x{self.cell_h}px",
            f"Actives: {active_cells}/{total_cells}",
            f"",
            "=== CONTROLES ===",
            "ENTREE: Definir reference",
            "Fleches: Deplacer grille",
            "+/-: Colonnes | *//: Lignes",
            "I/K: Largeur | L/J: Hauteur",
            "[/]: Seuil -/+ 5mm",
            "",
            "ESPACE: Sauver config",
            "C: Capture | R: Reset",
            "Q: Quitter"
        ]
        
        y = 20
        for text in help_text:
            if "Reference:" in text:
                color = ref_color
            elif "Actives:" in text:
                color = (0, 255, 255)  # Jaune
            else:
                color = (255, 255, 255)
            
            cv2.putText(image, text, (10, y), cv2.FONT_HERSHEY_SIMPLEX,
                       0.35, color, 1)
            y += 15
        
        return image
    
    def handle_key(self, key):
        """Gère les entrées clavier"""
        # === DÉPLACEMENT ===
        if key == 0 or key == ord('z') or key == ord('Z'):  # Haut
            self.start_y = max(0, self.start_y - 10)
        elif key == 1 or key == ord('s') or key == ord('S'):  # Bas
            self.start_y = min(424 - self.cell_h, self.start_y + 10)
        elif key == 2 or key == ord('a') or key == ord('A'):  # Gauche
            self.start_x = max(0, self.start_x - 10)
        elif key == 3 or key == ord('d') or key == ord('D'):  # Droite
            self.start_x = min(512 - self.cell_w, self.start_x + 10)
        
        # === NOMBRE DE CELLULES ===
        elif key == ord('+') or key == ord('='):
            self.cols = min(20, self.cols + 1)
        elif key == ord('-'):
            self.cols = max(1, self.cols - 1)
        elif key == ord('*'):
            self.rows = min(15, self.rows + 1)
        elif key == ord('/'):
            self.rows = max(1, self.rows - 1)
        
        # === TAILLE DES CELLULES ===
        elif key == ord('i') or key == ord('I'):
            self.cell_w = min(200, self.cell_w + 5)
        elif key == ord('k') or key == ord('K'):
            self.cell_w = max(20, self.cell_w - 5)
        elif key == ord('l') or key == ord('L'):
            self.cell_h = min(200, self.cell_h + 5)
        elif key == ord('j') or key == ord('J'):
            self.cell_h = max(20, self.cell_h - 5)
        
        # === SEUIL ===
        elif key == ord('['):
            self.threshold = max(5, self.threshold - 5)
            print(f"\n📏 Seuil: {self.threshold}mm ({self.threshold/10:.1f}cm)")
        elif key == ord(']'):
            self.threshold = min(200, self.threshold + 5)
            print(f"\n📏 Seuil: {self.threshold}mm ({self.threshold/10:.1f}cm)")
        
        # === RESET ===
        elif key == ord('r') or key == ord('R'):
            self.apply_default_config()
            self.reference_depth = None
            self.reference_set = False
            print("\n🔄 Tout réinitialisé")
    
    def run(self):
        """Boucle principale"""
        print("=" * 60)
        print("DÉTECTION BINAIRE D'OBJETS - KINECT V2")
        print("=" * 60)
        print("\n📌 INSTRUCTIONS:")
        print("1. Placez la Kinect face à la scène VIDE (fond)")
        print("2. Appuyez sur ENTRÉE pour définir la référence")
        print("3. Les objets plus proches apparaîtront en ROUGE")
        print("=" * 60)
        
        capture_count = 0
        current_depth = None
        
        while True:
            if self.kinect.has_new_depth_frame():
                # Récupérer la profondeur
                depth_frame = self.kinect.get_last_depth_frame()
                current_depth = depth_frame.reshape((424, 512)).astype(np.uint16)
                
                # Détecter les objets
                object_mask = self.detect_objects(current_depth)
                
                # Calculer les valeurs de la grille
                self.calculate_grid_values(object_mask)
                
                # Créer l'image binaire
                image = self.create_binary_image(current_depth, object_mask)
                
                # Dessiner la grille
                image = self.draw_grid(image)
                
                # Dessiner l'aide
                image = self.draw_help(image)
                
                # Afficher
                cv2.imshow('Detection Binaire', image)
            
            # Gestion des touches
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
            
            # === DÉFINIR LA RÉFÉRENCE ===
            elif key == 13:  # ENTRÉE
                if current_depth is not None:
                    self.set_reference(current_depth)
            
            # === SAUVEGARDER CONFIG ===
            elif key == 32:  # ESPACE
                self.save_config()
            
            # === CAPTURE ===
            elif key == ord('c') or key == ord('C'):
                if self.grid_values is not None:
                    # Sauvegarder l'image
                    img_file = f"capture_{capture_count}.png"
                    cv2.imwrite(img_file, image)
                    
                    # Sauvegarder les valeurs de la grille
                    grid_file = f"grid_{capture_count}.csv"
                    np.savetxt(grid_file, self.grid_values, delimiter=',', fmt='%d')
                    
                    print(f"\n📸 Sauvegardé: {img_file} et {grid_file}")
                    capture_count += 1
            
            # === AUTRES TOUCHES ===
            else:
                self.handle_key(key)
        
        cv2.destroyAllWindows()
        print("\n✅ Terminé!")


if __name__ == "__main__":
    detector = DepthDetector()
    detector.run()