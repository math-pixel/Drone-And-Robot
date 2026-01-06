#!/usr/bin/env python3
"""
DepthDetector utilisant un subprocess C++ pour la Kinect v2
Compatible Raspberry Pi 4
"""

import subprocess
import numpy as np
import os
import threading
import time


class DepthDetector:
    
    def __init__(self, delegate=None, grid_rows=3, grid_cols=3):
        self.delegate = delegate
        self.grid_rows = grid_rows
        self.grid_cols = grid_cols
        self.running = False
        self.process = None
        
        # Chemin vers l'exécutable C++
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.capture_bin = os.path.join(current_dir, "depth_capture")
        
        if not os.path.exists(self.capture_bin):
            raise FileNotFoundError(
                f"depth_capture non trouvé : {self.capture_bin}\n"
                "Compile-le avec la commande g++ fournie."
            )
    
    def _parse_grid_line(self, line):
        """
        Parse une ligne du format: "1234.5,2345.6,3456.7;1234.5,..."
        Retourne un numpy array 3x3
        """
        try:
            line = line.strip()
            if not line:
                return None
            
            rows = line.split(";")
            grid = []
            
            for row in rows:
                if row:
                    values = [float(v) for v in row.split(",") if v]
                    if values:
                        grid.append(values)
            
            if len(grid) == self.grid_rows:
                return np.array(grid)
            return None
            
        except Exception as e:
            print(f"⚠️ Erreur parsing: {e}")
            return None
    
    def run(self):
        """Boucle principale - bloquante"""
        print("🚀 Démarrage DepthDetector...")
        print(f"📍 Exécutable: {self.capture_bin}")
        
        try:
            # Lancer le programme C++ en subprocess
            self.process = subprocess.Popen(
                [self.capture_bin],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1  # Line buffered
            )
            
            self.running = True
            
            # Lire stderr pour les messages de statut
            def read_stderr():
                for line in self.process.stderr:
                    line = line.strip()
                    if line == "READY":
                        print("✅ Kinect v2 prête")
                    elif line == "NO_DEVICE":
                        print("❌ Aucune Kinect détectée")
                    elif line == "OPEN_FAILED":
                        print("❌ Impossible d'ouvrir la Kinect")
                    else:
                        print(f"[Kinect] {line}")
            
            stderr_thread = threading.Thread(target=read_stderr, daemon=True)
            stderr_thread.start()
            
            # Lire stdout pour les données de profondeur
            for line in self.process.stdout:
                if not self.running:
                    break
                
                grid = self._parse_grid_line(line)
                
                if grid is not None and self.delegate is not None:
                    self.delegate.process(grid)
                    
        except FileNotFoundError:
            print(f"❌ Exécutable non trouvé: {self.capture_bin}")
        except Exception as e:
            print(f"❌ Erreur: {e}")
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

if __name__ == "__main__":
    class TestDelegate:
        def process(self, grid):
            print("Grille reçue:")
            print(grid)
    
    detector = DepthDetector(delegate=TestDelegate())
    try:
        detector.run()
    except KeyboardInterrupt:
        detector.stop()
        print("Programme terminé.")