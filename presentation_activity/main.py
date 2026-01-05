import sys
import os
import numpy as np

# --- BLOC MAGIQUE A METTRE TOUT EN HAUT ---

# 1. On prend le chemin du fichier actuel (server.py)
current_path = os.path.abspath(__file__)

# 2. On prend le dossier du fichier (serveur/)
current_dir = os.path.dirname(current_path)

# 3. On remonte d'un cran pour avoir le dossier racine (PROJET/)
parent_dir = os.path.dirname(current_dir)

# 4. On ajoute la racine aux chemins de Python
sys.path.append(parent_dir)

# ------------------------------------------

from utils.WSServer import *
from utils.WSClient import *
from utils.kinect.DephDetector import DepthDetector

class DepthDetectorDelegate:

    def __init__(self):
        self.current_grid_completed = [[]]

    def joinGrid(self, grid_values):
        # Conversion en arrays numpy et OR logique
        self.current_grid_completed = np.logical_or(
            self.current_grid_completed, 
            grid_values
        ).astype(int)
   
    def isActivityFinish(self) -> bool:
        config_grid = self.load_config("config.json")["depth_detector"]["grid_validation"]
        config_array = np.array(config_grid)
        
        # Vérifie que tous les 1 de la grille de validation sont présents dans la grille actuelle
        # Les 1 supplémentaires dans la grille actuelle sont ignorés
        return np.all(self.current_grid_completed >= config_array)
        
    def playSound(self, grid_values):
        for row in range(grid_values.shape[0]):
            for col in range(grid_values.shape[1]):
                if grid_values[row, col] == 1:
                    print(f"Jouer le son pour la cellule ({row}, {col})")

    def process(self, grid_values):
        # Traiter les valeurs de la grille reçues du DepthDetector
        print("Grille de profondeur mise à jour:")
        print(grid_values)
        self.joinGrid(grid_values)
        if self.isActivityFinish():
            print("Envoie Activité terminée !")
        else:
            print("envoie Nouvelle donner recu sur la grille de profondeur.")

if __name__ == "__main__":
    config_path = os.path.join(parent_dir, "config.json")
    depth_detector_delegate = DepthDetectorDelegate()
    depth_detector = DepthDetector(delegate=depth_detector_delegate)