from pykinect2 import PyKinectV2
from pykinect2 import PyKinectRuntime
import numpy as np
import cv2

class DepthGrid:
    def __init__(self):
        # Position de départ
        self.start_x = 50
        self.start_y = 50
        
        # Nombre de cellules
        self.cols = 5
        self.rows = 4
        
        # Taille des cellules
        self.cell_w = 80
        self.cell_h = 70
        
        # Couleurs
        self.grid_color = (0, 255, 0)
        self.text_color = (255, 255, 255)
        self.bg_color = (0, 0, 0)
        
        # Kinect
        self.kinect = PyKinectRuntime.PyKinectRuntime(
            PyKinectV2.FrameSourceTypes_Depth
        )
    
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
                text = f"{avg/1000:.2f}m" if avg >= 1000 else f"{int(avg)}" if avg > 0 else "---"
                
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
        """Affiche l'aide"""
        help_text = [
            f"Position: ({self.start_x}, {self.start_y}) | Fleches: deplacer",
            f"Grille: {self.cols}x{self.rows} | +/-: colonnes | */.: lignes",
            f"Cellule: {self.cell_w}x{self.cell_h} | W/S: largeur | A/D: hauteur",
            "Q: Quitter | R: Reset | ESPACE: Sauvegarder"
        ]
        
        y = 20
        for text in help_text:
            cv2.putText(image, text, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 
                       0.4, (255, 255, 255), 1)
            y += 18
        
        return image
    
    def handle_key(self, key):
        """Gère les entrées clavier"""
        # Déplacement
        if key == 82 or key == ord('8'):    # Haut
            self.start_y = max(0, self.start_y - 10)
        elif key == 84 or key == ord('2'):  # Bas
            self.start_y = min(424, self.start_y + 10)
        elif key == 81 or key == ord('4'):  # Gauche
            self.start_x = max(0, self.start_x - 10)
        elif key == 83 or key == ord('6'):  # Droite
            self.start_x = min(512, self.start_x + 10)
        
        # Nombre de cellules
        elif key == ord('+') or key == ord('='):
            self.cols = min(20, self.cols + 1)
        elif key == ord('-'):
            self.cols = max(1, self.cols - 1)
        elif key == ord('*'):
            self.rows = min(15, self.rows + 1)
        elif key == ord('.'):
            self.rows = max(1, self.rows - 1)
        
        # Taille des cellules
        elif key == ord('w'):
            self.cell_w = min(200, self.cell_w + 5)
        elif key == ord('s'):
            self.cell_w = max(20, self.cell_w - 5)
        elif key == ord('d'):
            self.cell_h = min(200, self.cell_h + 5)
        elif key == ord('a'):
            self.cell_h = max(20, self.cell_h - 5)
        
        # Reset
        elif key == ord('r'):
            self.start_x, self.start_y = 50, 50
            self.cols, self.rows = 5, 4
            self.cell_w, self.cell_h = 80, 70
    
    def run(self):
        """Boucle principale"""
        print("=" * 60)
        print("GRILLE DE PROFONDEUR - CONTROLES INTERACTIFS")
        print("=" * 60)
        
        while True:
            if self.kinect.has_new_depth_frame():
                # Profondeur
                depth = self.kinect.get_last_depth_frame()
                depth = depth.reshape((424, 512)).astype(np.uint16)
                
                # Moyennes
                averages = self.calculate_averages(depth)
                
                # Image
                img = np.clip(depth, 500, 4500)
                img = ((img - 500) / 4000 * 255).astype(np.uint8)
                img = cv2.applyColorMap(img, cv2.COLORMAP_JET)
                img[depth == 0] = [0, 0, 0]
                
                # Dessiner
                img = self.draw(img, averages)
                img = self.draw_help(img)
                
                cv2.imshow('Grille de Profondeur', img)
            
            key = cv2.waitKey(1) & 0xFF
            
            if key == ord('q'):
                break
            elif key == ord(' '):
                # Sauvegarder
                np.savetxt('grid_averages.csv', averages, delimiter=',', fmt='%.1f')
                cv2.imwrite('grid_capture.png', img)
                print("✅ Sauvegardé!")
            elif key != 255:
                self.handle_key(key)
        
        cv2.destroyAllWindows()


if __name__ == "__main__":
    grid = DepthGrid()
    grid.run()