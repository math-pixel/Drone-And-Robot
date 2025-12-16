from pykinect2 import PyKinectV2
from pykinect2 import PyKinectRuntime
import numpy as np
import cv2

# ============================================
# PARAMÈTRES DE LA GRILLE (À MODIFIER)
# ============================================

# Position du coin supérieur gauche de la grille
GRID_START_X = 50      # Position X de départ (0-512)
GRID_START_Y = 50      # Position Y de départ (0-424)

# Nombre de cellules
GRID_COLS = 5          # Nombre de colonnes
GRID_ROWS = 4          # Nombre de lignes

# Taille de chaque cellule (en pixels)
CELL_WIDTH = 80        # Largeur d'une cellule
CELL_HEIGHT = 70       # Hauteur d'une cellule

# Couleurs (BGR)
GRID_COLOR = (0, 255, 0)       # Vert pour la grille
TEXT_COLOR = (255, 255, 255)   # Blanc pour le texte
BG_COLOR = (0, 0, 0)           # Noir pour le fond du texte

# ============================================

def calculate_grid_averages(depth_array, start_x, start_y, cols, rows, cell_w, cell_h):
    """
    Calcule la moyenne de profondeur pour chaque cellule de la grille
    
    Retourne une matrice (rows x cols) avec les moyennes en mm
    """
    averages = np.zeros((rows, cols), dtype=np.float32)
    
    for row in range(rows):
        for col in range(cols):
            # Coordonnées de la cellule
            x1 = start_x + col * cell_w
            y1 = start_y + row * cell_h
            x2 = x1 + cell_w
            y2 = y1 + cell_h
            
            # Vérifier les limites
            x1 = max(0, min(x1, 512))
            y1 = max(0, min(y1, 424))
            x2 = max(0, min(x2, 512))
            y2 = max(0, min(y2, 424))
            
            # Extraire la région
            cell_depth = depth_array[y1:y2, x1:x2]
            
            # Filtrer les valeurs valides (entre 500 et 8000 mm)
            valid_mask = (cell_depth > 0) & (cell_depth < 8000)
            valid_depths = cell_depth[valid_mask]
            
            # Calculer la moyenne
            if len(valid_depths) > 0:
                averages[row, col] = np.mean(valid_depths)
            else:
                averages[row, col] = 0  # Pas de données valides
    
    return averages


def draw_grid(image, start_x, start_y, cols, rows, cell_w, cell_h, averages):
    """
    Dessine la grille et affiche les moyennes sur l'image
    """
    for row in range(rows):
        for col in range(cols):
            # Coordonnées de la cellule
            x1 = start_x + col * cell_w
            y1 = start_y + row * cell_h
            x2 = x1 + cell_w
            y2 = y1 + cell_h
            
            # Dessiner le rectangle
            cv2.rectangle(image, (x1, y1), (x2, y2), GRID_COLOR, 2)
            
            # Calculer le centre de la cellule
            center_x = x1 + cell_w // 2
            center_y = y1 + cell_h // 2
            
            # Récupérer la moyenne
            avg = averages[row, col]
            
            if avg > 0:
                # Formater le texte (en mm ou m)
                if avg >= 1000:
                    text = f"{avg/1000:.2f}m"
                else:
                    text = f"{int(avg)}mm"
            else:
                text = "---"
            
            # Taille du texte
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.4
            thickness = 1
            
            # Obtenir la taille du texte pour centrer
            (text_w, text_h), _ = cv2.getTextSize(text, font, font_scale, thickness)
            
            # Position du texte (centré)
            text_x = center_x - text_w // 2
            text_y = center_y + text_h // 2
            
            # Fond pour le texte (meilleure lisibilité)
            padding = 2
            cv2.rectangle(image, 
                         (text_x - padding, text_y - text_h - padding),
                         (text_x + text_w + padding, text_y + padding),
                         BG_COLOR, -1)
            
            # Dessiner le texte
            cv2.putText(image, text, (text_x, text_y), 
                       font, font_scale, TEXT_COLOR, thickness)
    
    return image


def main():
    print("=" * 60)
    print("KINECT V2 - GRILLE DE PROFONDEUR")
    print("=" * 60)
    print(f"\nConfiguration:")
    print(f"  - Début: ({GRID_START_X}, {GRID_START_Y})")
    print(f"  - Grille: {GRID_COLS} x {GRID_ROWS} cellules")
    print(f"  - Taille cellule: {CELL_WIDTH} x {CELL_HEIGHT} pixels")
    print(f"\nCommandes:")
    print("  - 'q' : Quitter")
    print("  - 's' : Sauvegarder une capture")
    print("=" * 60)
    
    # Initialiser la Kinect
    kinect = PyKinectRuntime.PyKinectRuntime(
        PyKinectV2.FrameSourceTypes_Depth | 
        PyKinectV2.FrameSourceTypes_Color
    )
    
    print("\n✅ Kinect connectée!")
    
    capture_count = 0
    
    while True:
        if kinect.has_new_depth_frame():
            # Récupérer la profondeur
            depth_frame = kinect.get_last_depth_frame()
            depth_array = depth_frame.reshape((424, 512)).astype(np.uint16)
            
            # Calculer les moyennes de la grille
            averages = calculate_grid_averages(
                depth_array,
                GRID_START_X, GRID_START_Y,
                GRID_COLS, GRID_ROWS,
                CELL_WIDTH, CELL_HEIGHT
            )
            
            # Créer l'image de profondeur colorée
            depth_display = np.clip(depth_array, 500, 4500)
            depth_display = ((depth_display - 500) / 4000 * 255).astype(np.uint8)
            depth_color = cv2.applyColorMap(depth_display, cv2.COLORMAP_JET)
            
            # Marquer les zones invalides en noir
            depth_color[depth_array == 0] = [0, 0, 0]
            
            # Dessiner la grille
            depth_color = draw_grid(
                depth_color,
                GRID_START_X, GRID_START_Y,
                GRID_COLS, GRID_ROWS,
                CELL_WIDTH, CELL_HEIGHT,
                averages
            )
            
            # Afficher
            cv2.imshow('Grille de Profondeur', depth_color)
        
        # Gestion des touches
        key = cv2.waitKey(1) & 0xFF
        
        if key == ord('q'):
            break
        elif key == ord('s'):
            # Sauvegarder la capture
            filename = f"capture_{capture_count}.png"
            cv2.imwrite(filename, depth_color)
            print(f"\n📸 Capture sauvegardée: {filename}")
            
            # Sauvegarder aussi les données de la grille
            data_filename = f"grid_data_{capture_count}.txt"
            with open(data_filename, 'w') as f:
                f.write("Moyennes de profondeur (mm)\n")
                f.write("-" * 40 + "\n")
                for row in range(GRID_ROWS):
                    line = " | ".join([f"{averages[row, col]:7.1f}" for col in range(GRID_COLS)])
                    f.write(line + "\n")
            print(f"📊 Données sauvegardées: {data_filename}")
            
            capture_count += 1
    
    cv2.destroyAllWindows()
    print("\n✅ Terminé!")


if __name__ == "__main__":
    main()